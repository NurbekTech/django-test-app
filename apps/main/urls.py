from django.urls import path
from .views import dashboard, auth

app_name = "main"

urlpatterns = [
    path("auth/login/", auth.login_view, name="login"),
    path("auth/register/", auth.register_view, name="register"),
    path("auth/logout/", auth.logout_view, name="logout"),

    path("", dashboard.dashboard_view, name="dashboard"),
]
