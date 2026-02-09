from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from core.models import MCQSelection, SpeakingAnswer, PracticalSubmission, QuestionAttempt, SectionAttempt, ExamAttempt


# ======================================================================================================================
# QuestionAttempt
# ======================================================================================================================
# MCQSelectionInline
class MCQSelectionInline(admin.TabularInline):
    model = MCQSelection
    extra = 0


# SpeakingAnswerInline
class SpeakingAnswerInline(admin.StackedInline):
    model = SpeakingAnswer
    extra = 0


# PracticalSubmissionInline
class PracticalSubmissionInline(admin.StackedInline):
    model = PracticalSubmission
    extra = 0
    readonly_fields = ("passed", "failed", "total", "runtime_ms", "memory_kb", "verdict", "details", "checked_at", )


# QuestionAttemptAdmin
@admin.register(QuestionAttempt)
class QuestionAttemptAdmin(admin.ModelAdmin):
    list_display = ("question", "section_attempt", "is_answered", "is_graded", "score", "max_score", )
    list_filter = ("is_answered", "is_graded", "question__question_type")
    search_fields = ("question__prompt",)
    readonly_fields = ("created_at", "updated_at")

    inlines = (MCQSelectionInline, SpeakingAnswerInline, PracticalSubmissionInline, )


# ======================================================================================================================
# SectionAttempt
# ======================================================================================================================
# QuestionAttemptInline
class QuestionAttemptInline(admin.TabularInline):
    model = QuestionAttempt
    extra = 0
    readonly_fields = ("question", "score", "max_score", "is_answered", "is_graded")
    can_delete = False


# SectionAttemptAdmin
@admin.register(SectionAttempt)
class SectionAttemptAdmin(admin.ModelAdmin):
    list_display = ("attempt", "section", "status", "score", "max_score", "time_spent_seconds", )
    list_filter = ("status", "section__section_type")
    inlines = (QuestionAttemptInline, )


# ======================================================================================================================
# ExamAttempt
# ======================================================================================================================
# SectionAttemptInline
class SectionAttemptInline(admin.TabularInline):
    model = SectionAttempt
    extra = 0
    readonly_fields = ("section", "status", "score", "max_score", "time_spent_seconds", )
    can_delete = False


# ExamAttemptAdmin
@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "exam", "status", "started_at", "finished_at", "total_score", "max_total_score", )
    list_filter = ("status", "exam")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    autocomplete_fields = ("user", "exam")
    readonly_fields = ("started_at", "finished_at", "total_score", "max_total_score")
    inlines = (SectionAttemptInline, )
