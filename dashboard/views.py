from django.shortcuts import render

from exposure.models import FloodEvent


def index(request):
    event = FloodEvent.objects.order_by("-created_at").first()
    events = FloodEvent.objects.order_by("-created_at")[:10]
    return render(request, "dashboard/index.html", {"event": event, "events": events})
