from django.contrib import admin
from django.utils.translation import gettext_lazy as _


# ======================================================================================================================
# QuestionAttempt
# ======================================================================================================================
from core.models.attempts import (
    ExamAttempt,
    SectionAttempt,
    QuestionAttempt,
    SpeakingAnswer,
    PracticalSubmission,
    MCQSelection,
)

class MCQSelectionInline(admin.TabularInline):
    model = MCQSelection
    extra = 0


class SpeakingAnswerInline(admin.StackedInline):
    model = SpeakingAnswer
    extra = 0


class PracticalSubmissionInline(admin.StackedInline):
    model = PracticalSubmission
    extra = 0
    readonly_fields = (
        "passed",
        "failed",
        "total",
        "runtime_ms",
        "memory_kb",
        "verdict",
        "details",
        "checked_at",
    )


@admin.register(QuestionAttempt)
class QuestionAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "question",
        "section_attempt",
        "is_answered",
        "is_graded",
        "score",
        "max_score",
    )
    list_filter = ("is_answered", "is_graded", "question__question_type")
    search_fields = ("question__prompt",)
    readonly_fields = ("created_at", "updated_at")

    inlines = [
        MCQSelectionInline,
        SpeakingAnswerInline,
        PracticalSubmissionInline,
    ]


# ======================================================================================================================
# SectionAttempt
# ======================================================================================================================
class QuestionAttemptInline(admin.TabularInline):
    model = QuestionAttempt
    extra = 0
    readonly_fields = ("question", "score", "max_score", "is_answered", "is_graded")
    can_delete = False


@admin.register(SectionAttempt)
class SectionAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "attempt",
        "section",
        "status",
        "score",
        "max_score",
        "time_spent_seconds",
    )
    list_filter = ("status", "section__section_type")
    inlines = [QuestionAttemptInline]


# ======================================================================================================================
# ExamAttempt
# ======================================================================================================================
class SectionAttemptInline(admin.TabularInline):
    model = SectionAttempt
    extra = 0
    readonly_fields = ("section", "status", "score", "max_score", "time_spent_seconds")
    can_delete = False


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "exam",
        "status",
        "started_at",
        "finished_at",
        "total_score",
        "max_total_score",
    )
    list_filter = ("status", "exam")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    autocomplete_fields = ("user", "exam")

    readonly_fields = ("started_at", "finished_at", "total_score", "max_total_score")

    inlines = [SectionAttemptInline]