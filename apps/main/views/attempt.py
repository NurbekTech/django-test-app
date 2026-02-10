from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST
from apps.main.services.attempt import ensure_attempt_initialized, save_mcq_answer_only, \
    load_attempt_for_user, is_hx, finish_attempt_auto
from core.models import AttemptStatus, Question, QuestionAttempt, MCQSelection
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
