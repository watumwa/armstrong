"""Operations endpoints for reviewing and manually dispatching SMS reminders."""
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import SMSReminder
from .sms_reminders import dispatch_due_reminders, queue_due_reminders
from .views import check_role, log


def reminder_data(reminder):
    return {
        "id": str(reminder.id), "kind": reminder.kind, "facility_id": str(reminder.facility_id),
        "facility_name": reminder.facility.name, "recipient_phone": reminder.recipient_phone,
        "message": reminder.message, "scheduled_for": reminder.scheduled_for.isoformat(),
        "status": reminder.status, "provider_reference": reminder.provider_reference,
        "last_error": reminder.last_error, "sent_at": reminder.sent_at.isoformat() if reminder.sent_at else None,
        "created_at": reminder.created_at.isoformat(),
    }


@api_view(["GET"])
def reminder_list(request):
    check_role(request.user, "Administrator", "Supervisor", "Revenue Officer")
    rows = SMSReminder.objects.select_related("facility").order_by("-created_at")[:200]
    return Response({"reminders": [reminder_data(row) for row in rows]})


@api_view(["POST"])
def queue_reminders(request):
    check_role(request.user, "Administrator")
    queued = queue_due_reminders()
    log(request.user, "sms.reminders.queued", request.user)
    return Response({"queued": queued, "message": "Only clients with recorded SMS consent were queued."})


@api_view(["POST"])
def dispatch_reminders(request):
    check_role(request.user, "Administrator")
    result = dispatch_due_reminders()
    log(request.user, "sms.reminders.dispatched", request.user)
    return Response(result)
