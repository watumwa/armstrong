"""Printable collection confirmation, restricted to the assigned driver or managers."""
from django.http import HttpResponse
from django.utils.html import escape
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .fleet_models import StopVerification
from .views import check_role

@api_view(["GET"])
def receipt(request, verification_id):
    check_role(request.user,"Administrator","Supervisor","Waste Collector")
    v=StopVerification.objects.select_related("trip_stop__facility","trip_stop__trip__vehicle","driver").filter(pk=verification_id).first()
    if not v:return Response({"error":"Receipt not found"},status=404)
    if request.user.role=="Waste Collector" and v.driver_id!=request.user.id:
        return Response({"error":"Not permitted"},status=403)
    f=v.trip_stop.facility
    html=f"""<!doctype html><html><head><meta charset="utf-8"><title>Collection verification</title>
<style>body{{font-family:Arial,sans-serif;max-width:680px;margin:36px auto;padding:16px;color:#173044}}
h1{{font-size:24px}}dl{{display:grid;grid-template-columns:180px 1fr;gap:12px}}dt{{font-weight:bold}}
@media print{{button{{display:none}}}}</style></head><body>
<h1>Armstrong Global Solutions</h1><h2>Verified facility stop receipt</h2>
<dl><dt>Receipt ID</dt><dd>{escape(str(v.id))}</dd>
<dt>Facility</dt><dd>{escape(f.name)}</dd>
<dt>Driver</dt><dd>{escape(v.driver.name)}</dd>
<dt>Vehicle</dt><dd>{escape(v.trip_stop.trip.vehicle.registration)}</dd>
<dt>Verified at (UTC)</dt><dd>{escape(v.verified_at.isoformat())}</dd>
<dt>QR verified</dt><dd>{'Yes' if v.qr_verified else 'No'}</dd>
<dt>Geofence verified</dt><dd>{'Yes' if v.within_geofence else 'No'}</dd>
<dt>GPS accuracy</dt><dd>{v.accuracy_m:.1f} metres</dd>
<dt>Notes</dt><dd>{escape(v.notes)}</dd></dl>
<p>This confirms the facility stop was verified; it does not certify waste weight, transfer or disposal.</p>
<button onclick="window.print()">Print receipt</button></body></html>"""
    return HttpResponse(html,content_type="text/html; charset=utf-8",headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})
