from django.contrib import admin
from django.contrib.admin import register
from core.admin._mixins import LinkedAdminMixin
from core.forms.exams import ExamAdminForm, ExamSectionMaterialAdminForm, QuestionAdminForm, OptionAdminForm
from core.models import Exam, ExamSection, ExamSectionMaterial, Question, Option, SpeakingRubric, PracticalTestCase, \
    PracticalTask
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
# ======================================================================================================================
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
# ======================================================================================================================
class QuestionInline(LinkedAdminMixin, admin.TabularInline):
    model = Question
    exclude = ("prompt", )
    extra = 0
    readonly_fields = ("detail_link", )

    def detail_link(self, obj):
        return self.admin_link(obj, label=_("Толығырақ"))
    detail_link.short_description = _("Сілтеме")


# ExamSectionAdmin
# ======================================================================================================================
@register(ExamSection)
class ExamSectionAdmin(LinkedAdminMixin, admin.ModelAdmin):
    list_display = ("section_type", "max_score", )
    list_filter = ("section_type", )
    readonly_fields = ("exam_link", )

    def exam_link(self, obj):
        return self.parent_link(obj, 'exam')
    exam_link.short_description = _("Емтихан")

    inlines = (ExamSectionMaterialInline, QuestionInline, )


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
    max_num = 1


# PracticalTestCaseInline
class PracticalTestCaseInline(admin.TabularInline):
    model = PracticalTestCase
    extra = 0


# PracticalTaskInline
class PracticalTaskInline(admin.StackedInline):
    model = PracticalTask
    extra = 0


# QuestionAdmin
@admin.register(Question)
class QuestionAdmin(LinkedAdminMixin, admin.ModelAdmin):
    list_display = ("id", "section", "question_type", "points")
    list_filter = ("question_type", "section__section_type", "section__exam")
    search_fields = ("prompt", "section__exam__title")
    readonly_fields = ("section_link",)
    form = QuestionAdminForm

    def section_link(self, obj):
        return self.parent_link(obj, "section")
    section_link.short_description = _("Емтихан")

    inlines = [OptionInline, SpeakingRubricInline, PracticalTaskInline]
