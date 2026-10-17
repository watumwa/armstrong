"""Auditable invoicing, payment allocation, balances and printable receipts."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import uuid

from django.db import transaction
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.html import escape
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Facility, Invoice, InvoiceLine, Payment, PaymentAllocation
from .views import check_role, log


MONEY = Decimal("0.01")
OPEN_INVOICE_STATUSES = ("issued", "part_paid", "overdue")


def _money(value):
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def _decimal(value):
    try:
        amount = _money(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("A valid amount is required")
    if amount <= 0:
        raise ValueError("Amount must be greater than zero")
    return amount


def refresh_overdue_invoices(today=None):
    """Mark open past-due invoices server-side before any account response."""
    return Invoice.objects.filter(
        status__in=("issued", "part_paid"), due_date__lt=(today or timezone.localdate()), balance__gt=0
    ).update(status="overdue")


def invoice_data(invoice, include_lines=False):
    data = {
        "id": str(invoice.id),
        "facility_id": str(invoice.facility_id),
        "facility_name": invoice.facility.name,
        "invoice_number": invoice.invoice_number,
        "issue_date": invoice.issue_date.isoformat(),
        "due_date": invoice.due_date.isoformat(),
        "status": invoice.status,
        "currency": invoice.currency,
        "subtotal": str(invoice.subtotal),
        "amount_paid": str(invoice.amount_paid),
        "balance": str(invoice.balance),
        "notes": invoice.notes,
        "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
        "created_at": invoice.created_at.isoformat(),
    }
    if include_lines:
        data["lines"] = [{
            "id": str(line.id), "description": line.description, "quantity": str(line.quantity),
            "unit_price": str(line.unit_price), "line_total": str(line.line_total),
        } for line in invoice.lines.all()]
        data["allocations"] = [{
            "id": str(item.id), "payment_id": str(item.payment_id), "payment_reference": item.payment.reference,
            "amount": str(item.amount), "allocated_at": item.created_at.isoformat(),
        } for item in invoice.allocations.select_related("payment").order_by("created_at")]
    return data


def payment_data(payment):
    allocations = payment.allocations.select_related("invoice").order_by("created_at")
    allocated = sum((item.amount for item in allocations), Decimal("0.00"))
    return {
        "id": str(payment.id), "reference": payment.reference, "facility_id": str(payment.facility_id),
        "facility_name": payment.facility.name, "amount": str(payment.amount), "method": payment.method,
        "status": payment.status, "paid_at": payment.paid_at.isoformat(),
        "allocations": [{"invoice_id": str(item.invoice_id), "invoice_number": item.invoice.invoice_number,
                         "amount": str(item.amount)} for item in allocations],
        "unallocated_amount": str(_money(payment.amount - allocated)),
    }


@api_view(["GET", "POST"])
def invoices(request):
    check_role(request.user, "Administrator", "Supervisor", "Revenue Officer")
    refresh_overdue_invoices()
    if request.method == "GET":
        rows = Invoice.objects.select_related("facility").order_by("-issue_date", "-created_at")
        facility_id = request.query_params.get("facility_id")
        if facility_id:
            rows = rows.filter(facility_id=facility_id)
        return Response({"invoices": [invoice_data(row) for row in rows[:200]]})

    check_role(request.user, "Administrator", "Revenue Officer")
    due_date = parse_date(str(request.data.get("due_date", "")))
    if not due_date or due_date < timezone.localdate():
        return Response({"error": "A due date of today or later is required"}, status=400)
    lines = request.data.get("lines")
    if not isinstance(lines, list) or not 1 <= len(lines) <= 25:
        return Response({"error": "Provide 1 to 25 invoice lines"}, status=400)
    try:
        facility = Facility.objects.get(pk=request.data.get("facility_id"))
    except (Facility.DoesNotExist, ValueError, TypeError):
        return Response({"error": "Select a valid facility"}, status=400)

    prepared = []
    try:
        for raw in lines:
            if not isinstance(raw, dict):
                raise ValueError("Invalid invoice line")
            description = str(raw.get("description", "")).strip()
            quantity = Decimal(str(raw.get("quantity", "")))
            unit_price = _decimal(raw.get("unit_price"))
            if not description or len(description) > 300 or quantity <= 0:
                raise ValueError("Each line needs a description, quantity and unit price")
            quantity = quantity.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            prepared.append((description, quantity, unit_price, _money(quantity * unit_price)))
    except (InvalidOperation, ValueError, TypeError):
        return Response({"error": "Each line needs a valid description, positive quantity and positive unit price"}, status=400)
    subtotal = sum((line[3] for line in prepared), Decimal("0.00"))
    if subtotal <= 0:
        return Response({"error": "Invoice total must be greater than zero"}, status=400)

    with transaction.atomic():
        invoice = Invoice.objects.create(
            facility=facility, invoice_number="AGI-" + uuid.uuid4().hex[:12].upper(),
            issue_date=timezone.localdate(), due_date=due_date, status="issued", subtotal=subtotal,
            amount_paid=Decimal("0.00"), balance=subtotal, notes=str(request.data.get("notes", ""))[:2000],
            created_by=request.user, issued_at=timezone.now(),
        )
        InvoiceLine.objects.bulk_create([
            InvoiceLine(invoice=invoice, description=description, quantity=quantity, unit_price=unit_price, line_total=line_total)
            for description, quantity, unit_price, line_total in prepared
        ])
        log(request.user, "accounts.invoice.issued", invoice)
    invoice = Invoice.objects.select_related("facility").prefetch_related("lines").get(pk=invoice.pk)
    return Response({"invoice": invoice_data(invoice, include_lines=True)}, status=201)


@api_view(["GET"])
def invoice_detail(request, invoice_id):
    check_role(request.user, "Administrator", "Supervisor", "Revenue Officer")
    refresh_overdue_invoices()
    invoice = get_object_or_404(Invoice.objects.select_related("facility").prefetch_related("lines"), pk=invoice_id)
    return Response({"invoice": invoice_data(invoice, include_lines=True)})


@api_view(["POST"])
def confirm_payment(request, payment_id):
    check_role(request.user, "Administrator")
    allocations = request.data.get("allocations", [])
    if not isinstance(allocations, list) or len(allocations) > 50:
        return Response({"error": "Allocations must be a list of up to 50 items"}, status=400)
    try:
        with transaction.atomic():
            payment = Payment.objects.select_for_update().select_related("facility").get(pk=payment_id)
            if payment.status != "pending":
                return Response({"error": "Only pending payments can be confirmed"}, status=409)
            parsed = []
            seen = set()
            total = Decimal("0.00")
            for item in allocations:
                if not isinstance(item, dict) or str(item.get("invoice_id", "")) in seen:
                    raise ValueError("Each allocation needs a unique invoice")
                invoice_id = str(item.get("invoice_id", ""))
                amount = _decimal(item.get("amount"))
                seen.add(invoice_id)
                total += amount
                parsed.append((invoice_id, amount))
            if total > payment.amount:
                raise ValueError("Allocated amount cannot exceed received payment")
            invoice_map = {str(i.id): i for i in Invoice.objects.select_for_update().filter(pk__in=seen)}
            if len(invoice_map) != len(parsed):
                raise ValueError("One or more invoices were not found")
            for invoice_id, amount in parsed:
                invoice = invoice_map[invoice_id]
                if invoice.facility_id != payment.facility_id:
                    raise ValueError("Payments can only be allocated to the same facility")
                if invoice.status not in OPEN_INVOICE_STATUSES or amount > invoice.balance:
                    raise ValueError("Allocation exceeds an open invoice balance")
            for invoice_id, amount in parsed:
                invoice = invoice_map[invoice_id]
                PaymentAllocation.objects.create(payment=payment, invoice=invoice, amount=amount, allocated_by=request.user)
                invoice.amount_paid = _money(invoice.amount_paid + amount)
                invoice.balance = _money(invoice.balance - amount)
                invoice.status = "paid" if invoice.balance == 0 else "part_paid"
                invoice.save(update_fields=["amount_paid", "balance", "status"])
            payment.status = "confirmed"
            payment.save(update_fields=["status"])
            log(request.user, "accounts.payment.confirmed", payment)
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found"}, status=404)
    except (ValueError, InvalidOperation):
        return Response({"error": "Invalid payment allocations"}, status=400)
    payment = Payment.objects.select_related("facility").prefetch_related("allocations__invoice").get(pk=payment_id)
    return Response({"payment": payment_data(payment)})


@api_view(["GET"])
def payment_receipt(request, payment_id):
    check_role(request.user, "Administrator", "Supervisor", "Revenue Officer")
    payment = get_object_or_404(
        Payment.objects.select_related("facility", "received_by").prefetch_related("allocations__invoice"), pk=payment_id
    )
    if payment.status != "confirmed":
        return Response({"error": "A receipt is available only after payment confirmation"}, status=409)
    allocations = list(payment.allocations.select_related("invoice").order_by("created_at"))
    allocated = sum((allocation.amount for allocation in allocations), Decimal("0.00"))
    lines = "".join(
        f"<tr><td>{escape(allocation.invoice.invoice_number)}</td><td>UGX {allocation.amount:,.2f}</td></tr>"
        for allocation in allocations
    ) or "<tr><td colspan=\"2\">Unallocated payment credit</td></tr>"
    html = f"""<!doctype html><html><head><meta charset=\"utf-8\"><title>Payment receipt {escape(payment.reference)}</title>
<style>body{{font-family:Arial,sans-serif;max-width:700px;margin:36px auto;padding:16px;color:#173044}}h1{{font-size:24px}}table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #dbe4e9;text-align:left}}.total{{font-size:18px;font-weight:bold}}@media print{{button{{display:none}}}}</style></head><body>
<h1>Armstrong Global Solutions</h1><h2>Confirmed payment receipt</h2>
<table><tr><th>Receipt reference</th><td>{escape(payment.reference)}</td></tr><tr><th>Client</th><td>{escape(payment.facility.name)}</td></tr><tr><th>Payment method</th><td>{escape(payment.method)}</td></tr><tr><th>Received at</th><td>{escape(payment.paid_at.isoformat())}</td></tr><tr><th>Received by</th><td>{escape(payment.received_by.name if payment.received_by else 'System')}</td></tr></table>
<h3>Invoice allocation</h3><table><tr><th>Invoice</th><th>Allocated</th></tr>{lines}</table>
<p class=\"total\">Amount received: UGX {payment.amount:,.2f}</p><p>Unallocated credit: UGX {payment.amount - allocated:,.2f}</p>
<p>This is an operational payment receipt. Apply statutory tax-invoice controls before using it as a fiscal receipt.</p><button onclick=\"window.print()\">Print receipt</button></body></html>"""
    return HttpResponse(html, content_type="text/html; charset=utf-8", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@api_view(["GET"])
def account_summary(request):
    check_role(request.user, "Administrator", "Supervisor", "Revenue Officer")
    refresh_overdue_invoices()
    invoice_totals = Invoice.objects.aggregate(
        invoiced=Sum("subtotal"), outstanding=Sum("balance"), invoices=Count("id")
    )
    confirmed = Payment.objects.filter(status="confirmed").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    overdue = Invoice.objects.filter(status="overdue").aggregate(total=Sum("balance"))["total"] or Decimal("0.00")
    pending = Payment.objects.filter(status="pending").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    return Response({
        "currency": "UGX", "invoices": invoice_totals["invoices"] or 0,
        "invoiced": str(invoice_totals["invoiced"] or Decimal("0.00")),
        "outstanding": str(invoice_totals["outstanding"] or Decimal("0.00")),
        "overdue": str(overdue), "confirmed_payments": str(confirmed), "pending_payments": str(pending),
    })
