from ckeditor.widgets import CKEditorWidget
from django import forms
from core.models import Exam, Question, Option


# Exam
# ======================================================================================================================
class ExamAdminForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = "__all__"
        widgets = {
            "description": CKEditorWidget(config_name="default"),
        }


# ExamSectionMaterial
# ======================================================================================================================
class ExamSectionMaterialAdminForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = "__all__"
        widgets = {
            "text": CKEditorWidget(config_name="default"),
        }


# QuestionAdmin
# ======================================================================================================================
class QuestionAdminForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = "__all__"
        widgets = {
            "prompt": CKEditorWidget(config_name="default"),
        }


# OptionAdmin
# ======================================================================================================================
class OptionAdminForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = "__all__"
        widgets = {
            "text": CKEditorWidget(config_name="default"),
        }