from django.urls import path
from . import views

app_name = "customer"

urlpatterns = [
    # auth urls...
    path("", views.customer_dashboard_view, name="dashboard"),
]
