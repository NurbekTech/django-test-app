from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


# ======================================================================================================================
# Exam models
# ======================================================================================================================
# Exam
class Exam(models.Model):
    title = models.CharField(_("Тақырыбы"), max_length=255)
    description = models.TextField(_("Анықтама"), blank=True, null=True)
    is_published = models.BooleanField(_("Ашық емтихан"), default=True)
    created_at = models.DateTimeField(_("Жасалған уақыты"), auto_now_add=True)

    class Meta:
        verbose_name = _("Емтихан")
        verbose_name_plural = _("Емтихандар")

    def __str__(self):
        return self.title


# ExamSection
# ======================================================================================================================
class ExamSection(models.Model):
    class SectionType(models.TextChoices):
        LISTENING = "listening", _("Тыңдалым (Listening)")
        READING = "reading", _("Оқылым (Reading)")
        SPEAKING = "speaking", _("Айтылым (Speaking)")
        PRACTICAL = "practical", _("Жазылым (Writing/Practical)")

    exam = models.ForeignKey(
        Exam, related_name="sections",
        on_delete=models.CASCADE, verbose_name=_("Емтихан")
    )
    section_type = models.CharField(
        _("Секция түрі"), max_length=32,
        choices=SectionType.choices, default=SectionType.LISTENING
    )
    max_score = models.PositiveSmallIntegerField(_("Макс. баллы"), default=0)
    order = models.PositiveSmallIntegerField(_("Реттілік"), default=1)

    class Meta:
        verbose_name = _("Секция")
        verbose_name_plural = _("Секциялар")

    def __str__(self):
        return self.get_section_type_display()


# ExamSectionMaterial
# ======================================================================================================================
class ExamSectionMaterial(models.Model):
    section = models.OneToOneField(
        ExamSection, on_delete=models.CASCADE,
        related_name="material", verbose_name=_("Секция")
    )
    text = models.TextField(_("Мәтін"), blank=True, null=True)
    audio = models.FileField(_("Аудиожазба"), upload_to="exams/sounds/", blank=True, null=True)
    time_limit_seconds = models.PositiveSmallIntegerField(_("Уақыты (сек)"), default=0)
    order = models.PositiveSmallIntegerField(_("Реттілік"), default=1)

    class Meta:
        verbose_name = _("Секция материалы")
        verbose_name_plural = _("Секция материалдары")

    def __str__(self):
        return f"#{self.pk}: {self.section.section_type}"


