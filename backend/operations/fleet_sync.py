"""Offline field event sync. Client event IDs deduplicate accepted operations."""
import uuid
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .fleet_models import FleetSyncEvent
from .fleet_verification import process_verification
from .views import check_role

@api_view(["POST"])
def sync_events(request):
    check_role(request.user,"Waste Collector")
    events=request.data.get("events")
    if not isinstance(events,list) or not 1<=len(events)<=20:
        return Response({"error":"Provide 1 to 20 events"},status=400)
    results=[]
    for event in events:
        if not isinstance(event,dict):
            results.append({"status":"rejected","error":"Invalid event"});continue
        try:
            event_id=uuid.UUID(str(event.get("client_event_id")))
            stop_id=uuid.UUID(str(event.get("trip_stop_id")))
        except (ValueError,TypeError,AttributeError):
            results.append({"status":"rejected","error":"Invalid event or stop ID"});continue
        if event.get("event_type")!="stop.verify":
            results.append({"client_event_id":str(event_id),"status":"rejected","error":"Unsupported event type"});continue
        with transaction.atomic():
            prior=FleetSyncEvent.objects.select_for_update().filter(driver=request.user,client_event_id=event_id).first()
            if prior:
                results.append({"client_event_id":str(event_id),"status":prior.status,"result":prior.result,"replayed":True})
                continue
            # Keep the client's UUID for verification idempotency.
            class RequestProxy:
                user=request.user
                data={**event.get("payload",{}),"event_id":str(event_id)}
            response=process_verification(RequestProxy(),stop_id)
            status="accepted" if response.status_code in (200,201) else "rejected"
            result=dict(response.data)
            if status=="accepted":
                FleetSyncEvent.objects.create(driver=request.user,client_event_id=event_id,
                    event_type="stop.verify",trip_stop_id=stop_id,status=status,result=result)
            results.append({"client_event_id":str(event_id),"status":status,"result":result})
    return Response({"results":results})
