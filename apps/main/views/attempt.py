from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST
from apps.main.services.attempt import ensure_attempt_initialized, save_mcq_answer_only, \
    load_attempt_for_user, is_hx, finish_attempt_auto
from apps.main.services.speaking import transcribe_audio, match_keywords, score_speaking
from apps.main.services.writing import grade_writing_submission
from core.models import AttemptStatus, Question, QuestionAttempt, MCQSelection, ExamAttempt, SpeakingRubric, \
    SpeakingAnswer, WritingSubmission
from core.utils.decorators import role_required


# attempt detail page
# ======================================================================================================================
@require_GET
@role_required("customer")
def attempt_detail_view(request, attempt_id: int):
    attempt = load_attempt_for_user(request, attempt_id)
    ensure_attempt_initialized(attempt)

    if attempt.status in (AttemptStatus.FINISHED, AttemptStatus.ABORTED):
        return redirect("customer:attempt_review", attempt_id=attempt.pk)

    exam = attempt.exam
    sections = (
        exam.sections
        .all()
        .order_by("order")
        .select_related("material")
        .prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.order_by("order").prefetch_related("options"),
            )
        )
    )
    section_id = request.GET.get("section")
    section_id = int(section_id) if (section_id and section_id.isdigit()) else None
    section_map = {s.id: s for s in sections}
    current_section = section_map.get(section_id) if section_id else (sections[0] if sections else None)

    qa_qs = (
        QuestionAttempt.objects
        .filter(section_attempt__attempt=attempt)
        .select_related("question", "section_attempt")
    )
    qa_by_qid = {qa.question_id: qa for qa in qa_qs}

    selections = (
        MCQSelection.objects
        .filter(question_attempt__section_attempt__attempt=attempt)
        .values_list("question_attempt_id", "option_id")
    )
    selected_map = {}
    for qa_id, opt_id in selections:
        selected_map.setdefault(qa_id, set()).add(opt_id)

    readonly = attempt.status != AttemptStatus.IN_PROGRESS
    context = {
        "mode": "take",
        "readonly": readonly,
        "attempt": attempt,
        "sections": sections,
        "current_section": current_section,
        "qa_by_qid": qa_by_qid,
        "selected_map": selected_map,
        "AttemptStatus": AttemptStatus,
    }
    return render(request, "app/main/attempt/take.html", context)



# attempt answer action
# ======================================================================================================================
@require_POST
@role_required("customer")
def attempt_answer_view(request, attempt_id: int, question_id: int):
    attempt = load_attempt_for_user(request, attempt_id)
    if attempt.status != AttemptStatus.IN_PROGRESS:
        return redirect("main:attempt_review", attempt_id=attempt.pk)

    q = get_object_or_404(Question.objects.only("id", "question_type", "section_id"), pk=question_id)
    if q.question_type == "mcq_single":
        oid = request.POST.get("option")
        option_ids = [int(oid)] if (oid and oid.isdigit()) else []
        save_mcq_answer_only(attempt, question_id=q.pk, option_ids=option_ids)

    elif q.question_type == "mcq_multi":
        raw = request.POST.getlist("options")
        option_ids = [int(x) for x in raw if x.isdigit()]
        save_mcq_answer_only(attempt, question_id=q.pk, option_ids=option_ids)

    if is_hx(request):
        qa = QuestionAttempt.objects.get(section_attempt__attempt=attempt, question_id=q.pk)
        selected_set = set(
            MCQSelection.objects.filter(question_attempt=qa).values_list("option_id", flat=True)
        )

        html = render_to_string(
            "app/main/attempt/partials/question_card.html",
            {
                "mode": "take",
                "attempt": attempt,
                "q": q,
                "qa": qa,
                "selected_set": selected_set,
                "saved": True,
            },
            request=request,
        )
        return HttpResponse(html)

    return redirect(f"/attempts/{attempt.pk}/?section={q.section_id}")


# attempt speaking upload action
# ======================================================================================================================
@transaction.atomic
def attempt_speaking_upload_view(request, attempt_id: int, question_id: int):
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, user=request.user)

    if attempt.status != AttemptStatus.IN_PROGRESS:
        return redirect("customer:attempt_review", attempt_id=attempt.pk)

    qa = get_object_or_404(
        QuestionAttempt,
        section_attempt__attempt=attempt,
        question_id=question_id,
    )
    q = qa.question
    if q.question_type != "speaking_keywords":
        return redirect("customer:attempt_detail", attempt_id=attempt.pk)

    audio_file = request.FILES.get("audio")
    if not audio_file:
        # UI-да message шығарып, қайта көрсетуге болады
        return redirect("customer:attempt_detail", attempt_id=attempt.pk)

    # rubric міндетті
    rubric = get_object_or_404(SpeakingRubric, question=q)

    sa, _ = SpeakingAnswer.objects.get_or_create(question_attempt=qa)
    sa.audio = audio_file
    sa.save(update_fields=["audio"])

    # 1) транскрипция
    transcript = transcribe_audio(sa.audio.path)

    # 2) match + score
    matched = match_keywords(transcript, rubric.keywords)
    points = score_speaking(matched, rubric.point_per_keyword, rubric.max_points)

    # 3) SpeakingAnswer жаңарту
    sa.transcript = transcript
    sa.matched_keywords = matched
    sa.matched_count = len(matched)
    sa.save(update_fields=["transcript", "matched_keywords", "matched_count"])

    # 4) QuestionAttempt жаңарту
    qa.max_score = rubric.max_points
    qa.score = points
    qa.is_answered = True
    qa.is_graded = True
    qa.answer_json = {
        "type": "speaking_keywords",
        "transcript": transcript,
        "matched_keywords": matched,
    }
    qa.save(update_fields=["max_score", "score", "is_answered", "is_graded", "answer_json"])
    context = {
        "attempt": attempt,
        "q": q,
        "saved": True,
        "selected_set": set(),  # speaking-та қажет емес, бірақ шаблон күтсе
        "qa": qa,  # егер сен attempt_detail_view контекстінде qa беріп жүрсең
    }

    if is_hx(request):
        html = render_to_string(
            "app/main/attempt/partials/question_card.html",
            context,
            request=request
        )
        return HttpResponse(html)

    return redirect("customer:attempt_detail", attempt_id=attempt.pk)


# attempt writing submit action
@transaction.atomic
def attempt_writing_submit_view(request, attempt_id: int, question_id: int):
    attempt = load_attempt_for_user(request, attempt_id)

    if request.method != "POST":
        return redirect("customer:attempt_detail", attempt_id=attempt.pk)

    if attempt.status != AttemptStatus.IN_PROGRESS:
        return redirect("customer:attempt_review", attempt_id=attempt.pk)

    qa = get_object_or_404(
        QuestionAttempt,
        section_attempt__attempt=attempt,
        question_id=question_id,
    )

    output_text = (request.POST.get("output_text") or "").strip()
    code_text = request.POST.get("code") or ""

    sub, _ = WritingSubmission.objects.get_or_create(
        question_attempt=qa,
    )
    sub.code = code_text
    sub.output_text = output_text
    sub.save(update_fields=["code", "output_text"])

    # grade
    is_correct = grade_writing_submission(sub)

    # QuestionAttempt жаңарту
    qa.is_answered = True
    qa.is_graded = True
    qa.score = qa.max_score if is_correct else 0
    qa.save(update_fields=["is_answered", "is_graded", "score"])

    # HTMX болса тек карточканы қайтарамыз
    if is_hx(request):
        html = render_to_string(
            "app/main/attempt/partials/question_card.html",
            {
                "attempt": attempt,
                "q": qa.question,
                "qa": qa,
                "saved": True,
            },
            request=request
        )
        return HttpResponse(html)

    return redirect("customer:attempt_detail", attempt_id=attempt.pk)


# attempt_submit_view
@require_POST
@role_required("customer")
def attempt_submit_view(request, attempt_id: int):
    attempt = load_attempt_for_user(request, attempt_id)

    if attempt.status != AttemptStatus.IN_PROGRESS:
        return redirect("customer:attempt_review", attempt_id=attempt.pk)

    finish_attempt_auto(attempt)
    return redirect("customer:attempt_review", attempt_id=attempt.pk)


@require_GET
@role_required("customer")
def attempt_review_view(request, attempt_id: int):
    attempt = load_attempt_for_user(request, attempt_id)
    if attempt.status == AttemptStatus.IN_PROGRESS:
        return redirect("customer:attempt_detail", attempt_id=attempt.pk)

    ensure_attempt_initialized(attempt)
    sections = (
        attempt.exam.sections
        .all()
        .order_by("order")
        .select_related("material")
        .prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.order_by("order").prefetch_related("options"),
            )
        )
    )
    section_id = request.GET.get("section")
    section_id = int(section_id) if (section_id and section_id.isdigit()) else None
    section_map = {s.id: s for s in sections}
    current_section = section_map.get(section_id) if section_id else (sections[0] if sections else None)

    qa_qs = (
        QuestionAttempt.objects
        .filter(section_attempt__attempt=attempt)
        .select_related("question", "section_attempt")
    )
    qa_by_qid = {qa.question_id: qa for qa in qa_qs}

    selections = (
        MCQSelection.objects
        .filter(question_attempt__section_attempt__attempt=attempt)
        .values_list("question_attempt_id", "option_id")
    )
    selected_map = {}
    for qa_id, opt_id in selections:
        selected_map.setdefault(qa_id, set()).add(opt_id)

    correct_map = {}
    for sec in sections:
        for q in sec.questions.all():
            if q.question_type in ("mcq_single", "mcq_multi"):
                correct_map[q.id] = set(q.options.filter(is_correct=True).values_list("id", flat=True))

    context = {
        "mode": "review",
        "attempt": attempt,
        "sections": sections,
        "current_section": current_section,
        "qa_by_qid": qa_by_qid,
        "selected_map": selected_map,
        "correct_map": correct_map,
        "AttemptStatus": AttemptStatus,
    }
    return render(request, "app/main/attempt/review.html", context)
