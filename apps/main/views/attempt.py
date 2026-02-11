from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from core.utils.decorators import role_required
from django.views.decorators.http import require_GET, require_POST
from apps.main.services.attempt import ensure_attempt_initialized, save_mcq_answer_only, load_attempt_for_user, \
    is_hx, finish_attempt_auto
from apps.main.services.speaking import transcribe_audio, match_keywords, score_speaking
from apps.main.services.writing import grade_writing_submission
from core.models import AttemptStatus, Question, QuestionAttempt, MCQSelection, SpeakingRubric, SpeakingAnswer, \
    WritingSubmission


# attempt detail redirect
# ======================================================================================================================
@require_GET
@role_required("customer")
def attempt_detail_view(request, attempt_id: int):
    attempt = load_attempt_for_user(request, attempt_id)
    ensure_attempt_initialized(attempt)

    if attempt.status in (AttemptStatus.FINISHED, AttemptStatus.ABORTED):
        return redirect("customer:attempt_review", attempt_id=attempt.pk)

    sections = (
        attempt.exam.sections
        .all()
        .order_by("order")
        .prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.order_by("order"),
            )
        )
    )
    ordered_q_ids = []
    for sec in sections:
        ordered_q_ids.extend([q.id for q in sec.questions.all()])

    if not ordered_q_ids:
        return redirect("customer:attempt_review", attempt_id=attempt.pk)

    qa_qs = QuestionAttempt.objects.filter(section_attempt__attempt=attempt).only("question_id", "is_answered")
    answered_q_ids = {qa.question_id for qa in qa_qs if qa.is_answered}
    q_param = request.GET.get("q")
    if q_param and q_param.isdigit() and int(q_param) in ordered_q_ids:
        qid = int(q_param)
    else:
        qid = next((x for x in ordered_q_ids if x not in answered_q_ids), ordered_q_ids[0])

    url = reverse("customer:attempt_question", args=[attempt.pk])
    return redirect(f"{url}?q={qid}")


# ======================================================================================================================
# attempt question page
# ======================================================================================================================
@require_GET
@role_required("customer")
def attempt_question_view(request, attempt_id: int):
    attempt = load_attempt_for_user(request, attempt_id)
    ensure_attempt_initialized(attempt)

    if attempt.status in (AttemptStatus.FINISHED, AttemptStatus.ABORTED):
        return redirect("customer:attempt_review", attempt_id=attempt.pk)

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

    flat_questions = [q for sec in sections for q in sec.questions.all()]
    if not flat_questions:
        return redirect("customer:attempt_review", attempt_id=attempt.pk)

    q_ids = [q.id for q in flat_questions]
    q_param = request.GET.get("q")
    current_qid = int(q_param) if (q_param and q_param.isdigit() and int(q_param) in q_ids) else q_ids[0]
    qa_qs = (
        QuestionAttempt.objects
        .filter(section_attempt__attempt=attempt)
        .select_related("question", "section_attempt")
    )
    qa_by_qid = {qa.question_id: qa for qa in qa_qs}

    current_qa = qa_by_qid.get(current_qid)
    if not current_qa:
        ensure_attempt_initialized(attempt)
        current_qa = QuestionAttempt.objects.get(section_attempt__attempt=attempt, question_id=current_qid)
        qa_by_qid[current_qid] = current_qa

    current_q = current_qa.question
    current_section = None
    for sec in sections:
        if sec.id == current_q.section_id:
            current_section = sec
            break

    selected_set = set(
        MCQSelection.objects
        .filter(question_attempt=current_qa)
        .values_list("option_id", flat=True)
    )
    answered_q_ids = {qa.question_id for qa in qa_by_qid.values() if qa.is_answered}

    idx = q_ids.index(current_qid)
    prev_qid = q_ids[idx - 1] if idx > 0 else None
    next_qid = q_ids[idx + 1] if idx < len(q_ids) - 1 else None
    is_last = next_qid is None

    context = {
        "attempt": attempt,
        "flat_questions": flat_questions,
        "answered_q_ids": answered_q_ids,
        "current_section": current_section,
        "q": current_q,
        "qa": current_qa,
        "selected_set": selected_set,
        "prev_qid": prev_qid,
        "next_qid": next_qid,
        "q_index": idx + 1,
        "q_total": len(q_ids),
        "is_last": is_last,
    }
    return render(request, "app/main/attempt/question.html", context)


# ANSWER SAVE (HTMX ONLY)
# ======================================================================================================================
@role_required("customer")
def attempt_answer_view(request, attempt_id: int, question_id: int):
    attempt = load_attempt_for_user(request, attempt_id)
    if attempt.status != AttemptStatus.IN_PROGRESS:
        return redirect("customer:attempt_review", attempt_id=attempt.pk)

    # ТЕК HTMX
    if not is_hx(request):
        return redirect("customer:attempt_detail", attempt_id=attempt.pk)

    q = get_object_or_404(Question.objects.only("id", "question_type", "section_id"), pk=question_id)

    # 1) SAVE current answer
    if q.question_type == "mcq_single":
        oid = request.POST.get("option")
        option_ids = [int(oid)] if (oid and oid.isdigit()) else []
        save_mcq_answer_only(attempt, question_id=q.pk, option_ids=option_ids)

    elif q.question_type == "mcq_multi":
        raw = request.POST.getlist("options")
        option_ids = [int(x) for x in raw if x.isdigit()]
        save_mcq_answer_only(attempt, question_id=q.pk, option_ids=option_ids)

    # 2) Decide which question to render next
    next_qid = request.POST.get("next_qid")
    next_qid = int(next_qid) if (next_qid and next_qid.isdigit()) else q.pk

    # 3) Rebuild data for top boxes + next question panel
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
    flat_questions = [qq for sec in sections for qq in sec.questions.all()]
    q_ids = [qq.id for qq in flat_questions]
    if next_qid not in q_ids:
        next_qid = q_ids[0] if q_ids else q.pk

    qa_qs = (
        QuestionAttempt.objects
        .filter(section_attempt__attempt=attempt)
        .select_related("question", "section_attempt")
    )
    qa_by_qid = {qa.question_id: qa for qa in qa_qs}
    answered_q_ids = {qa.question_id for qa in qa_by_qid.values() if qa.is_answered}

    next_qa = qa_by_qid.get(next_qid)
    if not next_qa:
        next_qa = QuestionAttempt.objects.get(section_attempt__attempt=attempt, question_id=next_qid)

    selected_set = set(
        MCQSelection.objects
        .filter(question_attempt=next_qa)
        .values_list("option_id", flat=True)
    )

    idx = q_ids.index(next_qid)
    prev_qid = q_ids[idx - 1] if idx > 0 else None
    next2_qid = q_ids[idx + 1] if idx < len(q_ids) - 1 else None

    # current section (material көрсету үшін)
    current_section = None
    for s in sections:
        if s.id == next_qa.question.section_id:
            current_section = s
            break

    html = render_to_string(
        "app/main/attempt/partials/question_panel.html",
        {
            "attempt": attempt,
            "sections": sections,
            "flat_questions": flat_questions,
            "answered_q_ids": answered_q_ids,

            "q": next_qa.question,
            "qa": next_qa,
            "selected_set": selected_set,

            "prev_qid": prev_qid,
            "next_qid": next2_qid,
            "q_index": idx + 1,
            "q_total": len(q_ids),

            "current_section": current_section,
            "saved": True,
        },
        request=request,
    )
    return HttpResponse(html)


# ======================================================================================================================
# SPEAKING UPLOAD (HTMX friendly)
# ======================================================================================================================
@require_POST
@transaction.atomic
@role_required("customer")
def attempt_speaking_upload_view(request, attempt_id: int, question_id: int):
    attempt = load_attempt_for_user(request, attempt_id)
    if attempt.status != AttemptStatus.IN_PROGRESS:
        return redirect("customer:attempt_review", attempt_id=attempt.pk)

    qa = get_object_or_404(QuestionAttempt, section_attempt__attempt=attempt, question_id=question_id)
    q = qa.question

    if q.question_type != "speaking_keywords":
        return redirect("customer:attempt_detail", attempt_id=attempt.pk)

    audio_file = request.FILES.get("audio")
    if not audio_file:
        return redirect("customer:attempt_detail", attempt_id=attempt.pk)

    rubric = get_object_or_404(SpeakingRubric, question=q)

    sa, _ = SpeakingAnswer.objects.get_or_create(question_attempt=qa)
    sa.audio = audio_file
    sa.save(update_fields=["audio"])

    transcript = transcribe_audio(sa.audio.path)
    matched = match_keywords(transcript, rubric.keywords)
    points = score_speaking(matched, rubric.point_per_keyword, rubric.max_points)

    sa.transcript = transcript
    sa.matched_keywords = matched
    sa.matched_count = len(matched)
    sa.save(update_fields=["transcript", "matched_keywords", "matched_count"])

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

    if is_hx(request):
        html = render_to_string(
            "app/main/attempt/partials/question_card.html",
            {"mode": "take", "attempt": attempt, "q": q, "qa": qa, "saved": True, "selected_set": set()},
            request=request,
        )
        return HttpResponse(html)

    return redirect("customer:attempt_detail", attempt_id=attempt.pk)


# ======================================================================================================================
# WRITING SUBMIT (HTMX friendly)
# ======================================================================================================================
@require_POST
@transaction.atomic
@role_required("customer")
def attempt_writing_submit_view(request, attempt_id: int, question_id: int):
    attempt = load_attempt_for_user(request, attempt_id)

    if attempt.status != AttemptStatus.IN_PROGRESS:
        return redirect("customer:attempt_review", attempt_id=attempt.pk)

    qa = get_object_or_404(QuestionAttempt, section_attempt__attempt=attempt, question_id=question_id)

    output_text = (request.POST.get("output_text") or "").strip()
    code_text = request.POST.get("code") or ""

    sub, _ = WritingSubmission.objects.get_or_create(question_attempt=qa)
    sub.code = code_text
    sub.output_text = output_text
    sub.save(update_fields=["code", "output_text"])

    is_correct = grade_writing_submission(sub)

    qa.is_answered = True
    qa.is_graded = True
    qa.score = qa.max_score if is_correct else 0
    qa.save(update_fields=["is_answered", "is_graded", "score"])

    if is_hx(request):
        html = render_to_string(
            "app/main/attempt/partials/question_card.html",
            {"mode": "take", "attempt": attempt, "q": qa.question, "qa": qa, "saved": True},
            request=request,
        )
        return HttpResponse(html)

    return redirect("customer:attempt_detail", attempt_id=attempt.pk)


# ======================================================================================================================
# SUBMIT + REVIEW (as before)
# ======================================================================================================================
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
