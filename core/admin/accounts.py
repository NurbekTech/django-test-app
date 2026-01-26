from django.contrib import admin
from django.contrib.admin import register
from django.contrib.auth.admin import UserAdmin as UserModelAdmin
from django.contrib.auth.models import Group
from core.models import User


@register(User)
class UserAdmin(UserModelAdmin):
    model = User
    list_display = (
        "username",
        "email",
        'iin',
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "is_active",
        "date_joined",
    )
    list_filter = ("is_staff", "is_active")
    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
    )
    ordering = ("email",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "avatar",
                    "username",
                    "email",
                    'iin',
                    "first_name",
                    "last_name",
                    "password",
                )
            },
        ),
        (
            "Permissions",
            {"fields": ("is_staff", "is_active", "is_superuser", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login",)}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    'iin',
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


admin.site.unregister(Group)
