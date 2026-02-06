from django.db import models
from django.utils.translation import gettext_lazy as _


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
        _("Секция түрі"),
        max_length=32,
        choices=SectionType.choices,
        default=SectionType.LISTENING
    )
    max_score = models.PositiveSmallIntegerField(_("Макс. баллы"), default=0)
    time_limit_seconds = models.PositiveSmallIntegerField(_("Уақыты (сек)"), default=0)
    order = models.PositiveSmallIntegerField(_("Реттілік"), default=1)

    class Meta:
        verbose_name = _("Емтихан секциясы")
        verbose_name_plural = _("Емтихан секциялары")

    def __str__(self):
        return self.get_section_type_display()


# ExamSectionMaterial
# ======================================================================================================================
class ExamSectionMaterial(models.Model):
    section = models.ForeignKey(
        ExamSection, on_delete=models.CASCADE,
        related_name="materials", verbose_name=_("Емтихан секциясы")
    )
    text = models.TextField(_("Мәтін"), blank=True, null=True)
    audio = models.FileField(_("Аудиожазба"), upload_to="exams/sounds/", blank=True, null=True)
    order = models.PositiveSmallIntegerField(_("Реттілік"), default=1)

    class Meta:
        verbose_name = _("Секция материалы")
        verbose_name_plural = _("Секция материалдары")

    def __str__(self):
        return f"{self.section.section_type}: {self.pk}"


# Question
# ======================================================================================================================
class Question(models.Model):
    class QuestionType(models.TextChoices):
        MCQ_SINGLE = "mcq_single", _("Бір жауапты")
        MCQ_MULTI = "mcq_multi", _("Көп жауапты")
        SPEAKING_KEYWORDS = "speaking_keywords", _("Айтылым")
        PRACTICAL_CODE = "practical_code", _("Жазбаша")

    section = models.ForeignKey(
        ExamSection, on_delete=models.CASCADE,
        related_name="questions", verbose_name=_("Емтихан секциясы")
    )
    question_type = models.CharField(_("Сұрақ типі"), max_length=32, choices=QuestionType.choices)
    prompt = models.TextField(_("Берілгені"))
    points = models.PositiveSmallIntegerField(_("Ұпай"), default=1)

    def __str__(self):
        return self.prompt[:60]

    class Meta:
        verbose_name = _("Сұрақ")
        verbose_name_plural = _("Сұрақтар")


# ======================================================================================================================
# Question type
# ======================================================================================================================
# Option
class Option(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE,
        related_name="options", verbose_name=_("Сұрақ")
    )
    text = models.TextField(_("Жауап"))
    is_correct = models.BooleanField(_("Дұрыс жауап"), default=False)

    def __str__(self):
        return self.text[:60]


# Speaking
# ======================================================================================================================
class SpeakingRubric(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE,
        related_name="speaking_rubrics", verbose_name=_("Сұрақ")
    )
    keywords = models.JSONField(_("Кілттік сөздер"), default=list)
    point_per_keyword = models.PositiveSmallIntegerField(_("Кілттік сөз баллы"), default=3)
    max_points = models.PositiveSmallIntegerField(_("Макс. балл"), default=25)

    def __str__(self):
        return self.pk


# Writing
# ======================================================================================================================
class PracticalTask(models.Model):
    question = models.OneToOneField(
        Question, on_delete=models.CASCADE,
        related_name="practical_task", verbose_name=_("Сұрақ")
    )
    input_spec = models.TextField(blank=True)
    output_spec = models.TextField(blank=True)
    sample_input = models.TextField(blank=True)
    sample_output = models.TextField(blank=True)

    def __str__(self):
        return self.pk


class PracticalTestCase(models.Model):
    task = models.ForeignKey(
        PracticalTask, on_delete=models.CASCADE,
        related_name="test_cases", verbose_name=_("Тапсырма")
    )
    input_data = models.TextField(_("Дерек енгізу"))
    expected_output = models.TextField()
    is_public = models.BooleanField(default=False)
    weight = models.PositiveIntegerField(default=1)
