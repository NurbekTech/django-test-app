from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.conf import settings


def role_required(*allowed_roles, redirect_url=None, raise_403=False):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = getattr(request, "user", None)

            if not user or not user.is_authenticated:
                return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)

            user_role = getattr(user, "role", None)
            if getattr(user, "is_superuser", False):
                return view_func(request, *args, **kwargs)

            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)

            if raise_403 or not redirect_url:
                return HttpResponseForbidden("Access denied")

            return redirect(redirect_url)
        return _wrapped
    return decorator
