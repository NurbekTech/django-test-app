from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ======================================================================================================================
# Attempts (submission layer)
# ======================================================================================================================
# AttemptStatus
class AttemptStatus(models.TextChoices):
    DRAFT = "draft", _("Басталды")
    SUBMITTED = "submitted", _("Жіберілді")
    GRADED = "graded", _("Бағаланды")
    CANCELLED = "cancelled", _("Болдырылмады")


# ExamAttempt
class ExamAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="exam_attempts", verbose_name=_("Пайдаланушы"),
    )
    exam = models.ForeignKey(
        "Exam", on_delete=models.CASCADE,
        related_name="attempts", verbose_name=_("Емтихан"),
    )
    status = models.CharField(_("Статус"), max_length=16, choices=AttemptStatus.choices, default=AttemptStatus.DRAFT)
    started_at = models.DateTimeField(_("Басталған уақыты"), default=timezone.now)
    finished_at = models.DateTimeField(_("Аяқталған уақыты"), blank=True, null=True)
    total_score = models.DecimalField(_("Жалпы балл"), max_digits=7, decimal_places=2, default=0)
    max_total_score = models.DecimalField(_("Макс жалпы балл"), max_digits=7, decimal_places=2, default=0)
    meta = models.JSONField(_("Қосымша дерек"), default=dict, blank=True)

    class Meta:
        verbose_name = _("Емтихан тапсыру")
        verbose_name_plural = _("Емтихан тапсырулар")
        indexes = [
            models.Index(fields=["user", "exam", "started_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Attempt#{self.pk} {self.user} - {self.exam}"

    def mark_submitted(self):
        self.status = AttemptStatus.SUBMITTED
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])


# SectionAttempt
class SectionAttempt(models.Model):
    attempt = models.ForeignKey(
        ExamAttempt, on_delete=models.CASCADE,
        related_name="section_attempts", verbose_name=_("Емтихан тапсыру"),
    )
    section = models.ForeignKey(
        "ExamSection", on_delete=models.CASCADE,
        related_name="attempts", verbose_name=_("Емтихан секциясы"),
    )
    status = models.CharField(_("Статус"), max_length=16, choices=AttemptStatus.choices, default=AttemptStatus.DRAFT)
    started_at = models.DateTimeField(_("Басталған уақыты"), blank=True, null=True)
    finished_at = models.DateTimeField(_("Аяқталған уақыты"), blank=True, null=True)
    score = models.DecimalField(_("Секция баллы"), max_digits=7, decimal_places=2, default=0)
    max_score = models.DecimalField(_("Макс секция баллы"), max_digits=7, decimal_places=2, default=0)
    time_spent_seconds = models.PositiveIntegerField(_("Жұмсаған уақыт (сек)"), default=0)

    class Meta:
        verbose_name = _("Секция тапсыруы")
        verbose_name_plural = _("Секция тапсырулары")
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "section"],
                name="uniq_section_attempt_per_attempt",
            )
        ]
        indexes = [
            models.Index(fields=["attempt", "section"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.attempt} / {self.section}"


# QuestionAttempt
class QuestionAttempt(models.Model):
    section_attempt = models.ForeignKey(
        SectionAttempt, on_delete=models.CASCADE,
        related_name="question_attempts", verbose_name=_("Секция тапсыруы"),
    )
    question = models.ForeignKey(
        "Question", on_delete=models.CASCADE,
        related_name="attempts", verbose_name=_("Сұрақ"),
    )
    answer_json = models.JSONField(_("Жауап (JSON)"), default=dict, blank=True)
    score = models.DecimalField(_("Ұпай"), max_digits=7, decimal_places=2, default=0)
    max_score = models.DecimalField(_("Макс ұпай"), max_digits=7, decimal_places=2, default=0)
    is_answered = models.BooleanField(_("Жауап берілді"), default=False)
    is_graded = models.BooleanField(_("Бағаланды"), default=False)
    created_at = models.DateTimeField(_("Құрылған уақыты"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Жаңартылған уақыты"), auto_now=True)

    class Meta:
        verbose_name = _("Сұрақ жауабы")
        verbose_name_plural = _("Сұрақ жауаптары")
        constraints = [
            models.UniqueConstraint(
                fields=["section_attempt", "question"],
                name="uniq_question_attempt_per_section_attempt",
            )
        ]
        indexes = [
            models.Index(fields=["section_attempt", "question"]),
            models.Index(fields=["is_answered", "is_graded"]),
        ]

    def __str__(self):
        return f"QA#{self.pk} {self.question_id}"


# ======================================================================================================================
# Specialized answers (optional but recommended)
# ======================================================================================================================
# SpeakingAnswer
class SpeakingAnswer(models.Model):
    question_attempt = models.OneToOneField(
        "QuestionAttempt",
        on_delete=models.CASCADE,
        related_name="speaking_answer",
        verbose_name=_("QuestionAttempt"),
    )

    audio = models.FileField(_("Аудио жауап"), upload_to="exams/speaking/", blank=True, null=True)
    transcript = models.TextField(_("Транскрипт"), blank=True, null=True)
    matched_count = models.PositiveSmallIntegerField(_("Табылған сөз саны"), default=0)
    matched_keywords = models.JSONField(_("Табылған кілт сөздер"), default=list, blank=True)

    def __str__(self):
        return f"SpeakingAnswer#{self.pk}"

    class Meta:
        verbose_name = _("Speaking жауабы")
        verbose_name_plural = _("Speaking жауаптары")


# PracticalSubmission
class PracticalSubmission(models.Model):
    class Language(models.TextChoices):
        PYTHON = "python", _("Python")
        CPP = "cpp", _("C++")
        JAVA = "java", _("Java")
        JS = "js", _("JavaScript")

    question_attempt = models.OneToOneField(
        QuestionAttempt, on_delete=models.CASCADE,
        related_name="practical_submission", verbose_name=_("QuestionAttempt"),
    )

    language = models.CharField(_("Тіл"), max_length=16, choices=Language.choices, default=Language.PYTHON)
    code = models.TextField(_("Код"), blank=True, null=True)
    passed = models.PositiveIntegerField(_("Өткен тест саны"), default=0)
    failed = models.PositiveIntegerField(_("Құлаған тест саны"), default=0)
    total = models.PositiveIntegerField(_("Барлық тест саны"), default=0)
    runtime_ms = models.PositiveIntegerField(_("Runtime (ms)"), default=0)
    memory_kb = models.PositiveIntegerField(_("Memory (kb)"), default=0)
    verdict = models.CharField(_("Verdict"), max_length=64, blank=True, null=True)  # AC / WA / TLE / RE ...
    details = models.JSONField(_("Толық нәтиже (JSON)"), default=dict, blank=True)
    checked_at = models.DateTimeField(_("Тексерілген уақыты"), blank=True, null=True)

    class Meta:
        verbose_name = _("Practical жіберілім")
        verbose_name_plural = _("Practical жіберілімдер")

    def __str__(self):
        return f"PracticalSubmission#{self.pk}"


# MCQSelection
class MCQSelection(models.Model):
    question_attempt = models.ForeignKey(
        QuestionAttempt, on_delete=models.CASCADE,
        related_name="mcq_selections", verbose_name=_("QuestionAttempt"),
    )
    option = models.ForeignKey(
        "Option", on_delete=models.CASCADE,
        related_name="selections", verbose_name=_("Option"),
    )

    class Meta:
        verbose_name = _("MCQ таңдау")
        verbose_name_plural = _("MCQ таңдаулар")
        constraints = [
            models.UniqueConstraint(
                fields=["question_attempt", "option"],
                name="uniq_mcq_selection",
            )
        ]
