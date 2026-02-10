from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from core.models.attempts import (
    ExamAttempt, SectionAttempt, QuestionAttempt,
    AttemptStatus, MCQSelection,
)


def load_attempt_for_user(request, attempt_id: int) -> ExamAttempt:
    return get_object_or_404(
        ExamAttempt.objects.select_related("exam"),
        pk=attempt_id,
        user=request.user,
    )


def is_hx(request):
    return request.headers.get("HX-Request") == "true"


# ensure_attempt_initialized
@transaction.atomic
def ensure_attempt_initialized(attempt: ExamAttempt) -> None:
    exam = attempt.exam

    if attempt.status == AttemptStatus.NO_STARTED:
        attempt.status = AttemptStatus.IN_PROGRESS
        attempt.save(update_fields=["status"])

    sections = list(
        exam.sections.all().order_by("order").prefetch_related("questions")
    )
    existing_sa = {
        sa.section_id: sa
        for sa in attempt.section_attempts.select_related("section").all()
    }
    section_attempts_to_create = []
    for sec in sections:
        if sec.id not in existing_sa:
            section_attempts_to_create.append(
                SectionAttempt(
                    attempt=attempt,
                    section=sec,
                    status=AttemptStatus.NO_STARTED,
                    max_score=Decimal(str(sec.max_score or 0)),
                )
            )

    if section_attempts_to_create:
        SectionAttempt.objects.bulk_create(section_attempts_to_create)

    existing_sa = {
        sa.section_id: sa
        for sa in attempt.section_attempts.select_related("section").all()
    }
    existing_qa = set(
        QuestionAttempt.objects.filter(section_attempt__attempt=attempt)
        .values_list("question_id", flat=True)
    )
    qa_to_create = []
    for sec in sections:
        sa = existing_sa[sec.id]
        for q in sec.questions.all().order_by("order"):
            if q.id in existing_qa:
                continue
            qa_to_create.append(
                QuestionAttempt(
                    section_attempt=sa,
                    question=q,
                    max_score=Decimal(str(q.points or 0)),
                )
            )

    if qa_to_create:
        QuestionAttempt.objects.bulk_create(qa_to_create)

    max_total = sum((sec.max_score or 0) for sec in sections)
    attempt.max_total_score = Decimal(str(max_total))
    attempt.save(update_fields=["max_total_score"])


# recalc_attempt_scores
def recalc_attempt_scores(attempt: ExamAttempt) -> None:
    for sa in attempt.section_attempts.all():
        s = sa.question_attempts.aggregate(total=Sum("score"))["total"] or Decimal("0")
        if sa.score != s:
            sa.score = s
            sa.save(update_fields=["score"])

    total = attempt.section_attempts.aggregate(total=Sum("score"))["total"] or Decimal("0")
    if attempt.total_score != total:
        attempt.total_score = total
        attempt.save(update_fields=["total_score"])


# save_mcq_answer_only
@transaction.atomic
def save_mcq_answer_only(attempt, question_id: int, option_ids: list[int]) -> None:
    if attempt.status != AttemptStatus.IN_PROGRESS:
        return

    qa = (
        QuestionAttempt.objects
        .select_related("question", "section_attempt")
        .prefetch_related("question__options")
        .get(section_attempt__attempt=attempt, question_id=question_id)
    )

    q = qa.question

    valid_option_ids = set(q.options.values_list("id", flat=True))
    chosen = [oid for oid in option_ids if oid in valid_option_ids]

    MCQSelection.objects.filter(question_attempt=qa).delete()
    MCQSelection.objects.bulk_create(
        [MCQSelection(question_attempt=qa, option_id=oid) for oid in chosen]
    )

    qa.answer_json = {"selected_option_ids": chosen}
    qa.is_answered = len(chosen) > 0

    qa.save(update_fields=["answer_json", "is_answered"])


# grade_attempt_mcq
@transaction.atomic
def grade_attempt_mcq(attempt) -> None:
    qas = (
        QuestionAttempt.objects
        .filter(section_attempt__attempt=attempt, question__question_type__in=["mcq_single", "mcq_multi"])
        .select_related("question")
        .prefetch_related("question__options")
    )

    selected = {}
    for qa_id, opt_id in MCQSelection.objects.filter(question_attempt__in=qas).values_list("question_attempt_id", "option_id"):
        selected.setdefault(qa_id, set()).add(opt_id)

    for qa in qas:
        q = qa.question
        chosen_set = selected.get(qa.pk, set())
        correct_ids = set(q.options.filter(is_correct=True).values_list("id", flat=True))

        score = Decimal("0")
        points = Decimal(str(q.points or 0))

        if q.question_type == "mcq_single":
            if len(chosen_set) == 1 and chosen_set == correct_ids:
                score = points
        elif q.question_type == "mcq_multi":
            if chosen_set == correct_ids and len(correct_ids) > 0:
                score = points

        qa.score = score
        qa.is_graded = True
        qa.save(update_fields=["score", "is_graded"])

    recalc_attempt_scores(attempt)


# finish_attempt_auto
@transaction.atomic
def finish_attempt_auto(attempt: ExamAttempt) -> None:
    if attempt.status != AttemptStatus.IN_PROGRESS:
        return

    grade_attempt_mcq(attempt)

    attempt.status = AttemptStatus.FINISHED
    attempt.save(update_fields=["status"])