from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


# User model
# ----------------------------------------------------------------------------------------------------------------------
class User(AbstractUser):
    USER_ROLES = (
        ("customer", _("Тапсырушы")),
        ("manager", _("Менеджер")),
    )

    avatar = models.ImageField(_("Аватар"), upload_to="accounts/users/avatars", null=True, blank=True)
    iin = models.CharField(_("ЖСН"), max_length=36, unique=True)
    role = models.CharField(_("Типі"), max_length=20, choices=USER_ROLES, default="customer")

    def __str__(self):
        return f"{self.first_name} + {self.last_name}"

    class Meta:
        verbose_name = _("Қолданушы")
        verbose_name_plural = _("Қолданушылар")
