from django.urls import path
from .views import customer, auth, account, attempt

app_name = "main"

urlpatterns = [
    path("auth/login/", auth.login_view, name="login"),
    path("auth/register/", auth.register_view, name="register"),
    path("auth/logout/", auth.logout_view, name="logout"),

    path('account/me/', account.account_view, name="account"),
    path('account/settings/', account.settings_view, name="settings"),

    path("", customer.customer_dashboard_view, name="dashboard"),
    path("exams/", customer.customer_exams_view, name="exams"),
    path("exams/<int:exam_id>/", customer.customer_exam_detail_view, name="exam_detail"),
    path("exams/<int:exam_id>/start/", customer.customer_exam_start_view, name="exam_start"),

    path("attempts/<int:attempt_id>/", attempt.attempt_detail_view, name="attempt_detail"),
    path("attempts/<int:attempt_id>/review/", attempt.attempt_review_view, name="attempt_review"),
    path("attempts/<int:attempt_id>/submit/", attempt.attempt_submit_view, name="attempt_submit"),
    path("attempts/<int:attempt_id>/answer/<int:question_id>/", attempt.attempt_answer_view, name="attempt_answer"),
]
