from django.shortcuts import render
from core.utils.decorators import role_required


@role_required("customer", redirect_url="/customer/dashboard")
def customer_dashboard_view(request):
    return render(request, "app/customer/page.html", {})
