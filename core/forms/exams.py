from ckeditor.widgets import CKEditorWidget
from django import forms
from core.models import Exam


# Exam
# ----------------------------------------------------------------------------------------------------------------------
class ExamAdminForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Exam
        fields = '__all__'



class ExamSectionMaterialAdminForm(forms.ModelForm):
    text = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Exam
        fields = '__all__'