"""Consent-aware SMS reminder outbox with an optional Twilio transport."""
import base64
import json
import os
from datetime import timedelta
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.db import IntegrityError
from django.utils import timezone

from .accounts_api import refresh_overdue_invoices
from .models import Collection, Invoice, SMSReminder


class SMSConfigurationError(RuntimeError):
    pass


def _money(value):
    return f"{Decimal(value):,.0f}"


def queue_due_reminders(now=None, horizon_hours=48):
    """Queue one consented reminder per eligible collection/invoice event."""
    now = now or timezone.now()
    refresh_overdue_invoices(now.date())
    queued = {"upcoming_collection": 0, "overdue_balance": 0}
    collections = Collection.objects.select_related("facility").filter(
        status__in=("scheduled", "en_route"),
        scheduled_at__gte=now,
        scheduled_at__lte=now + timedelta(hours=horizon_hours),
        facility__sms_opt_in=True,
    )
    for collection in collections.iterator():
        key = f"collection:{collection.id}:upcoming:v1"
        message = (
            f"Armstrong reminder: collection for {collection.facility.name} is scheduled for "
            f"{timezone.localtime(collection.scheduled_at).strftime('%d %b, %I:%M %p')}."
        )
        try:
            SMSReminder.objects.create(
                reminder_key=key, facility=collection.facility, collection=collection,
                kind="upcoming_collection", recipient_phone=collection.facility.phone,
                message=message[:480], scheduled_for=now,
            )
            queued["upcoming_collection"] += 1
        except IntegrityError:
            pass

    invoices = Invoice.objects.select_related("facility").filter(
        status="overdue", balance__gt=0, facility__sms_opt_in=True
    )
    for invoice in invoices.iterator():
        key = f"invoice:{invoice.id}:overdue:{now.date().isoformat()}"
        message = (
            f"Armstrong reminder: invoice {invoice.invoice_number} has an overdue balance of UGX "
            f"{_money(invoice.balance)}. Please contact our accounts team."
        )
        try:
            SMSReminder.objects.create(
                reminder_key=key, facility=invoice.facility, invoice=invoice, kind="overdue_balance",
                recipient_phone=invoice.facility.phone, message=message[:480], scheduled_for=now,
            )
            queued["overdue_balance"] += 1
        except IntegrityError:
            pass
    return queued


def _twilio_send(to, body):
    account_sid = os.environ.get("SMS_TWILIO_ACCOUNT_SID", "")
    auth_token = os.environ.get("SMS_TWILIO_AUTH_TOKEN", "")
    from_number = os.environ.get("SMS_TWILIO_FROM", "")
    if not all((account_sid, auth_token, from_number)):
        raise SMSConfigurationError("Twilio SMS configuration is incomplete")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = urlencode({"To": to, "From": from_number, "Body": body}).encode("utf-8")
    auth = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
    request = Request(url, data=payload, headers={"Authorization": f"Basic {auth}"}, method="POST")
    try:
        with urlopen(request, timeout=12) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"SMS provider request failed: {str(exc)[:180]}") from exc
    sid = parsed.get("sid")
    if not sid:
        raise RuntimeError("SMS provider did not return a message reference")
    return str(sid)


def send_reminder(reminder):
    """Send a queued row. No provider config means it remains queued, not sent."""
    provider = os.environ.get("SMS_PROVIDER", "").strip().lower()
    if provider != "twilio":
        raise SMSConfigurationError("SMS_PROVIDER=twilio is required before dispatching reminders")
    reference = _twilio_send(reminder.recipient_phone, reminder.message)
    reminder.status = "sent"
    reminder.provider_reference = reference
    reminder.last_error = None
    reminder.sent_at = timezone.now()
    reminder.save(update_fields=["status", "provider_reference", "last_error", "sent_at"])
    return reference


def dispatch_due_reminders(limit=100, now=None):
    now = now or timezone.now()
    rows = list(SMSReminder.objects.filter(status="queued", scheduled_for__lte=now).order_by("scheduled_for")[:limit])
    result = {"sent": 0, "failed": 0, "not_configured": False, "attempted": len(rows)}
    for row in rows:
        try:
            send_reminder(row)
            result["sent"] += 1
        except SMSConfigurationError:
            result["not_configured"] = True
            break
        except RuntimeError as exc:
            row.status = "failed"
            row.last_error = str(exc)[:500]
            row.save(update_fields=["status", "last_error"])
            result["failed"] += 1
    return result
