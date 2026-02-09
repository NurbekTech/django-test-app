from django.shortcuts import render
from core.utils.decorators import role_required


@role_required(["manager"])
def dashboard_view(request):
    return render(request, "app/page.html", {})
