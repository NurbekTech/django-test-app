from django.db.models import OuterRef, Exists, Prefetch
from django.db.models.aggregates import Avg
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET

from core.utils.decorators import role_required
from core.models import ExamAttempt, SectionAttempt, Exam, Section, Question, AttemptStatus


@role_required("customer")
def customer_dashboard_view(request):
    user = request.user

    # 1) Соңғы 10 attempt (finished ғана көрсетеміз)
    recent_attempts = (
        ExamAttempt.objects
        .filter(user=user)
        .order_by("-finished_at", "-id")[:10]
    )

    # 2) Жалпы орташа баға (attempt.total_score бойынша)
    # total_score null болса Avg есепті бұзбау үшін exclude қыламыз
    overall_avg = (
        ExamAttempt.objects
        .filter(user=user)
        .exclude(total_score__isnull=True)
        .aggregate(avg=Avg("total_score"))
        .get("avg")
    )

    # 3) 4 секция бойынша орташа (SectionAttempt.score бойынша)
    # SectionAttempt -> section FK арқылы section_type алып отырмыз деп есептеймін
    section_avgs_qs = (
        SectionAttempt.objects
        .filter(attempt__user=user)  # <-- ОСЫ ЖЕР ТҮЗЕТІЛДІ
        .exclude(score__isnull=True)
        .values("section__section_type")  # мұны өзіңнің Section өрісіңе қарай өзгертуің мүмкін
        .annotate(avg=Avg("score"))
    )

    section_avgs = {row["section__section_type"]: row["avg"] for row in section_avgs_qs}

    # 4) UI үшін тұрақты 4 секцияны дайындап береміз
    # Сенің нақты кодтарың қандай екенін білмеймін, сондықтан стандарт қылып тұрмын:
    # "listening", "reading", "writing", "speaking"
    SECTION_KEYS = [
        ("listening", "Listening"),
        ("reading", "Reading"),
        ("writing", "Writing"),
        ("speaking", "Speaking"),
    ]

    section_progress = []
    for key, label in SECTION_KEYS:
        section_progress.append({
            "key": key,
            "label": label,
            "avg": section_avgs.get(key),  # жоқ болса None
        })

    # 5) Прогресс пайыздарын шығару (егер score 0..100 формат болса — тура)
    # Егер score 0..10/0..40 сияқты болса, UI-да % қылу үшін нормализация керек.
    # Әзірше "avg" мәнін сол күйі көрсетеміз.

    context = {
        "profile_user": user,
        "overall_avg": overall_avg,
        "section_progress": section_progress,
        "recent_attempts": recent_attempts,
    }
    return render(request, "app/page.html", context)



@role_required("customer")
def customer_exams_view(request):
    user = request.user
    user_has_attempt = ExamAttempt.objects.filter(
        user=user,
        exam_id=OuterRef("pk"),
    )
    exams = (
        Exam.objects
        .all()
        .order_by("-id")
        .annotate(is_registered=Exists(user_has_attempt))
    )
    return render(request, "app/exams/page.html", {"exams": exams})


@role_required("customer")
def customer_exam_detail_view(request, exam_id: int):
    user = request.user
    exam_qs = (
        Exam.objects
        .annotate(
            is_registered=Exists(
                ExamAttempt.objects.filter(user=user, exam_id=OuterRef("pk"))
            )
        )
        .prefetch_related(
            Prefetch(
                "sections",
                queryset=Section.objects.order_by("order").prefetch_related(
                    Prefetch("questions", queryset=Question.objects.order_by("order"))
                ),
            )
        )
    )
    exam = get_object_or_404(exam_qs, pk=exam_id)

    # Ең соңғы active attempt (status-ты өзіңе қарай нақтылаймыз)
    active_attempt = (
        ExamAttempt.objects
        .filter(user=user, exam=exam)
        .exclude(status="finished")   # <- status мәнің басқа болса ауыстырасың
        .order_by("-id")
        .first()
    )

    context = {
        "exam": exam,
        "active_attempt": active_attempt,
    }
    return render(request, "app/exams/detail/page.html", context)


@role_required("customer")
def customer_exam_start_view(request, exam_id: int):
    exam = get_object_or_404(Exam, pk=exam_id)
    user = request.user

    # 1) Егер аяқталмаған attempt бар болса — соны қолдан
    # NOTE: status атауы сенде қандай екенін білмеймін.
    # Егер status="in_progress" / "started" болса соған ауыстыр.
    active_attempt = (
        ExamAttempt.objects
        .filter(user=user, exam=exam)
        .exclude(status="finished")   # <-- статус мәнін өз жобаңа қарай нақтылаймыз
        .order_by("-id")
        .first()
    )

    if active_attempt:
        return redirect("main:attempt_detail", attempt_id=active_attempt.pk)

    # 2) Жаңа attempt құру
    attempt = ExamAttempt.objects.create(
        user=user,
        exam=exam,
        status="started",           # <-- статус мәнін өз жобаңа қарай нақтылаймыз
        started_at=timezone.now(),  # егер auto_now_add болса, бұл жолды алып таста
    )

    return redirect("main:attempt_detail", attempt_id=attempt.pk)
