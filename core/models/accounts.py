from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    avatar = models.ImageField(_("Avatar"), upload_to="users/avatars", null=True)

    def __str__(self):
        return f"{self.first_name} + {self.last_name}"

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
