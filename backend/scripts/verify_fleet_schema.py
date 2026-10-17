"""Read-only structural verification of Armstrong fleet schema."""
import os
import psycopg

TABLES = {
    "fleet_vehicles": {"id", "registration", "label", "status"},
    "fleet_assignments": {"id", "vehicle_id", "driver_id", "assigned_by_id", "ended_at"},
    "fleet_trips": {"id", "vehicle_id", "driver_id", "created_by_id", "status", "scheduled_for"},
    "fleet_trip_stops": {"id", "trip_id", "facility_id", "sequence", "status"},
    "fleet_alerts": {"id", "alert_key", "trip_id", "severity", "category", "resolved_at"},
    "fleet_sync_events": {"id", "driver_id", "client_event_id", "event_type", "trip_stop_id", "status", "result"},
    "fleet_stop_verifications": {"id", "trip_stop_id", "driver_id", "event_id", "within_geofence", "qr_verified"},
    "fleet_location_pings": {"id", "trip_id", "driver_id", "latitude", "longitude", "accuracy_m", "client_event_id"},
}
with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        for table, required in TABLES.items():
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s", (table,))
            columns = {row[0] for row in cur.fetchall()}
            missing = required - columns
            if missing:
                raise RuntimeError(f"{table} missing columns: {sorted(missing)}")
            print(f"OK: {table} ({len(columns)} columns)")
print("Fleet database structure verified.")
