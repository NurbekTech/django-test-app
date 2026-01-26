from django.contrib import admin
from django.contrib.admin import register
from core.admin._mixins import LinkedAdminMixin
from core.forms.exams import ExamAdminForm, ExamSectionMaterialAdminForm
from core.models import Exam, ExamSection, ExamSectionMaterial
from django.utils.translation import gettext_lazy as _


# Exam
# ----------------------------------------------------------------------------------------------------------------------
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



# ExamSection
# ----------------------------------------------------------------------------------------------------------------------
# ExamSectionMaterialInline
class ExamSectionMaterialInline(admin.StackedInline):
    model = ExamSectionMaterial
    extra = 0
    form = ExamSectionMaterialAdminForm


# ExamSectionAdmin
@register(ExamSection)
class ExamSectionAdmin(LinkedAdminMixin, admin.ModelAdmin):
    list_display = ("section_type", "max_score", "time_limit_seconds", )
    list_filter = ("section_type", )
    readonly_fields = ("exam_link", )

    def exam_link(self, obj):
        return self.parent_link(obj, 'exam')
    exam_link.short_description = _("Емтихан")

    inlines = (ExamSectionMaterialInline, )
