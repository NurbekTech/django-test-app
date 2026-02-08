from django.contrib import admin
from django.contrib.admin import register
from django.utils.safestring import mark_safe

from core.admin._mixins import LinkedAdminMixin
from core.forms.exams import ExamAdminForm, ExamSectionMaterialAdminForm, QuestionAdminForm, OptionAdminForm, \
    SpeakingRubricAdminForm
from core.models import Exam, ExamSection, ExamSectionMaterial, Question, Option, PracticalTestCase, SpeakingRubric
from django.utils.translation import gettext_lazy as _


# ======================================================================================================================
# Exam
# ======================================================================================================================
# ExamSectionInline
class ExamSectionInline(LinkedAdminMixin, admin.TabularInline):
    model = ExamSection
    extra = 0
    readonly_fields = ("detail_link", )

    def detail_link(self, obj):
        return self.admin_link(obj, label=_("Толығырақ"))
    detail_link.short_description = _("Сілтеме")


# ExamAdmin
@register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "created_at", )
    list_filter = ("is_published", )
    search_fields = ("title", )
    form = ExamAdminForm

    inlines = (ExamSectionInline, )


# ======================================================================================================================
# ExamSection
# ======================================================================================================================
# ExamSectionMaterialInline
class ExamSectionMaterialInline(LinkedAdminMixin, admin.StackedInline):
    model = ExamSectionMaterial
    extra = 0
    form = ExamSectionMaterialAdminForm


# QuestionInline
class QuestionInline(LinkedAdminMixin, admin.TabularInline):
    model = Question
    fields = ("order", "question_type", "points", "detail_link", )
    extra = 0
    readonly_fields = ("detail_link", )

    def detail_link(self, obj):
        return self.admin_link(obj, label=_("Толығырақ"))
    detail_link.short_description = _("Сілтеме")


# ExamSectionAdmin
@register(ExamSection)
class ExamSectionAdmin(LinkedAdminMixin, admin.ModelAdmin):
    list_display = ("section_type", "max_score", )
    list_filter = ("section_type", )
    readonly_fields = ("exam_link", )

    def exam_link(self, obj):
        return self.parent_link(obj, 'exam')
    exam_link.short_description = _("Емтихан")

    inlines = (ExamSectionMaterialInline, QuestionInline, )

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)
        if obj is None:
            return []

        if obj.section_type in (
                ExamSection.SectionType.LISTENING,
                ExamSection.SectionType.READING,
        ):
            return inline_instances

        return [inl for inl in inline_instances if inl.__class__ is not ExamSectionMaterialInline]


# ======================================================================================================================
# Question
# ======================================================================================================================
# OptionInline
class OptionInline(admin.TabularInline):
    model = Option
    extra = 0
    form = OptionAdminForm


# SpeakingRubricInline
class SpeakingRubricInline(admin.StackedInline):
    model = SpeakingRubric
    extra = 0
    form = SpeakingRubricAdminForm


# PracticalTestCaseInline
class PracticalTestCaseInline(LinkedAdminMixin, admin.StackedInline):
    model = PracticalTestCase
    extra = 0
    readonly_fields = ("detail_link", )

    def detail_link(self, obj):
        return self.admin_link(obj, label=_("Толығырақ"))
    detail_link.short_description = _("Сілтеме")


# QuestionAdmin
@admin.register(Question)
class QuestionAdmin(LinkedAdminMixin, admin.ModelAdmin):
    list_display = ("preview", "section", "question_type", "points")
    list_filter = ("question_type", "section__section_type", "section__exam")
    search_fields = ("prompt", "section__exam__title")
    readonly_fields = ("section_link",)
    form = QuestionAdminForm

    def preview(self, obj):
        html = obj.prompt or ''
        return mark_safe(f"<div class='preview'>{html}</div>")

    def section_link(self, obj):
        return self.parent_link(obj, "section")
    section_link.short_description = _("Емтихан")

    inlines = [OptionInline, PracticalTestCaseInline, SpeakingRubricInline]

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)
        if obj is None:
            return []

        qt = obj.question_type

        allowed = set()

        if qt in (Question.QuestionType.MCQ_SINGLE, Question.QuestionType.MCQ_MULTI):
            allowed.add(OptionInline)

        if qt == Question.QuestionType.SPEAKING_KEYWORDS:
            allowed.add(SpeakingRubricInline)

        if qt == Question.QuestionType.PRACTICAL_CODE:
            allowed.add(PracticalTestCaseInline)

        return [inl for inl in inline_instances if inl.__class__ in allowed]


# ======================================================================================================================
# PracticalTaskAdmin
# ======================================================================================================================
@admin.register(PracticalTestCase)
class PracticalTestCaseAdmin(LinkedAdminMixin, admin.ModelAdmin):
    list_display = ("question", "is_public", "weight" )
    search_fields = ("question__prompt", )
    readonly_fields = ("question_link", )

    def question_link(self, obj):
        return self.parent_link(obj, "question")
    question_link.short_description = _("Сұрақ")
