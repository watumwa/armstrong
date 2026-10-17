-- Armstrong PostgreSQL schema. Apply once to a dedicated database.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS users(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),name text NOT NULL,email text NOT NULL UNIQUE,role text NOT NULL CHECK(role IN ('Administrator','Supervisor','Waste Collector','Revenue Officer','Marketer')),password_hash text NOT NULL,active boolean NOT NULL DEFAULT true,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS facilities(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),code text NOT NULL UNIQUE,name text NOT NULL,type text NOT NULL,address text NOT NULL,district text NOT NULL DEFAULT 'Kampala',phone text NOT NULL,latitude double precision,longitude double precision,monthly_fee numeric(12,2) NOT NULL DEFAULT 0 CHECK(monthly_fee>=0),collection_day text,created_at timestamptz NOT NULL DEFAULT now(),CHECK(latitude BETWEEN -90 AND 90),CHECK(longitude BETWEEN -180 AND 180));
CREATE TABLE IF NOT EXISTS agreements(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),facility_id uuid NOT NULL REFERENCES facilities(id),reference text UNIQUE NOT NULL,status text NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','active','expired','terminated')),start_date date,end_date date,monthly_fee numeric(12,2) NOT NULL CHECK(monthly_fee>=0),created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS collections(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),facility_id uuid NOT NULL REFERENCES facilities(id),collector_id uuid REFERENCES users(id),scheduled_at timestamptz NOT NULL,status text NOT NULL DEFAULT 'scheduled' CHECK(status IN ('scheduled','en_route','arrived','submitted','verified','rejected','missed')),waste_category text,bags integer CHECK(bags>=0),weight_kg numeric(12,3) CHECK(weight_kg>=0),notes text,verified_by uuid REFERENCES users(id),verified_at timestamptz,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS payments(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),facility_id uuid NOT NULL REFERENCES facilities(id),received_by uuid REFERENCES users(id),amount numeric(12,2) NOT NULL CHECK(amount>0),method text NOT NULL,reference text UNIQUE NOT NULL,status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','confirmed','void')),paid_at timestamptz NOT NULL DEFAULT now(),created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS audit_log(id bigserial PRIMARY KEY,actor_id uuid REFERENCES users(id),action text NOT NULL,entity_type text NOT NULL,entity_id text NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_collections_facility_date ON collections(facility_id,scheduled_at DESC);
CREATE INDEX IF NOT EXISTS idx_payments_facility_date ON payments(facility_id,paid_at DESC);
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS sms_opt_in boolean NOT NULL DEFAULT false;
ALTER TABLE facilities ADD COLUMN IF NOT EXISTS sms_opt_in_at timestamptz;

-- Fleet phase 1: additive, idempotent schema; no existing rows modified.
CREATE TABLE IF NOT EXISTS fleet_vehicles (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 registration text NOT NULL UNIQUE,
 label text NOT NULL,
 status text NOT NULL DEFAULT 'available' CHECK(status IN ('available','maintenance','inactive')),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS fleet_assignments (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 vehicle_id uuid NOT NULL REFERENCES fleet_vehicles(id),
 driver_id uuid NOT NULL REFERENCES users(id),
 assigned_by_id uuid NOT NULL REFERENCES users(id),
 assigned_at timestamptz NOT NULL DEFAULT now(),
 ended_at timestamptz,
 CHECK(ended_at IS NULL OR ended_at >= assigned_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS fleet_active_vehicle_assignment ON fleet_assignments(vehicle_id) WHERE ended_at IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS fleet_active_driver_assignment ON fleet_assignments(driver_id) WHERE ended_at IS NULL;
CREATE TABLE IF NOT EXISTS fleet_trips (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 vehicle_id uuid NOT NULL REFERENCES fleet_vehicles(id),
 driver_id uuid NOT NULL REFERENCES users(id),
 created_by_id uuid NOT NULL REFERENCES users(id),
 status text NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','active','completed','cancelled')),
 scheduled_for timestamptz NOT NULL,
 started_at timestamptz,
 ended_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK(ended_at IS NULL OR (started_at IS NOT NULL AND ended_at>=started_at))
);
CREATE UNIQUE INDEX IF NOT EXISTS fleet_active_vehicle_trip ON fleet_trips(vehicle_id) WHERE status='active';
CREATE UNIQUE INDEX IF NOT EXISTS fleet_active_driver_trip ON fleet_trips(driver_id) WHERE status='active';
CREATE TABLE IF NOT EXISTS fleet_trip_stops (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 trip_id uuid NOT NULL REFERENCES fleet_trips(id),
 facility_id uuid NOT NULL REFERENCES facilities(id),
 sequence integer NOT NULL CHECK(sequence>0),
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','arrived','completed','missed')),
 arrived_at timestamptz,
 completed_at timestamptz,
 UNIQUE(trip_id,sequence), UNIQUE(trip_id,facility_id)
);
CREATE INDEX IF NOT EXISTS fleet_trips_driver_schedule ON fleet_trips(driver_id,scheduled_for DESC);

-- Phase 2: consent-based GPS reporting during active trips.
CREATE TABLE IF NOT EXISTS fleet_location_pings (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 trip_id uuid NOT NULL REFERENCES fleet_trips(id),
 driver_id uuid NOT NULL REFERENCES users(id),
 latitude double precision NOT NULL CHECK(latitude BETWEEN -90 AND 90),
 longitude double precision NOT NULL CHECK(longitude BETWEEN -180 AND 180),
 accuracy_m double precision NOT NULL CHECK(accuracy_m >= 0 AND accuracy_m <= 10000),
 captured_at timestamptz NOT NULL,
 received_at timestamptz NOT NULL DEFAULT now(),
 client_event_id uuid NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS fleet_location_trip_time ON fleet_location_pings(trip_id,captured_at DESC);
CREATE INDEX IF NOT EXISTS fleet_location_driver_time ON fleet_location_pings(driver_id,received_at DESC);

-- Phase 3: facility arrival verification and collection proof
CREATE TABLE IF NOT EXISTS fleet_stop_verifications (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 trip_stop_id uuid NOT NULL REFERENCES fleet_trip_stops(id),
 driver_id uuid NOT NULL REFERENCES users(id),
 event_id uuid NOT NULL UNIQUE,
 latitude double precision NOT NULL CHECK(latitude BETWEEN -90 AND 90),
 longitude double precision NOT NULL CHECK(longitude BETWEEN -180 AND 180),
 accuracy_m double precision NOT NULL CHECK(accuracy_m BETWEEN 0 AND 1000),
 distance_m double precision,
 within_geofence boolean,
 qr_verified boolean NOT NULL DEFAULT false,
 verified_at timestamptz NOT NULL DEFAULT now(),
 notes text NOT NULL DEFAULT '',
 UNIQUE(trip_stop_id)
);
CREATE INDEX IF NOT EXISTS fleet_verifications_driver_time ON fleet_stop_verifications(driver_id,verified_at DESC);

-- Phase 4: durable server-side sync acknowledgements, one per driver event.
CREATE TABLE IF NOT EXISTS fleet_sync_events (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 driver_id uuid NOT NULL REFERENCES users(id),
 client_event_id uuid NOT NULL,
 event_type text NOT NULL CHECK(event_type IN ('stop.verify')),
 trip_stop_id uuid NOT NULL REFERENCES fleet_trip_stops(id),
 status text NOT NULL CHECK(status IN ('accepted','rejected')),
 result jsonb NOT NULL DEFAULT '{}'::jsonb,
 received_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(driver_id,client_event_id)
);
CREATE INDEX IF NOT EXISTS fleet_sync_events_driver_time ON fleet_sync_events(driver_id,received_at DESC);

-- Phase 5: persisted operational exceptions and notification outbox (no paid provider dependency).
CREATE TABLE IF NOT EXISTS fleet_alerts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 alert_key text NOT NULL UNIQUE,
 trip_id uuid REFERENCES fleet_trips(id),
 severity text NOT NULL CHECK(severity IN ('warning','critical')),
 category text NOT NULL,
 message text NOT NULL,
 resolved_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS fleet_alerts_unresolved ON fleet_alerts(created_at DESC) WHERE resolved_at IS NULL;

-- Phase 6: staff-phone trip tracking. Tracking starts and stops only through
-- an explicit driver action; it is not background surveillance.
CREATE TABLE IF NOT EXISTS fleet_tracking_sessions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 trip_id uuid NOT NULL REFERENCES fleet_trips(id),
 driver_id uuid NOT NULL REFERENCES users(id),
 consented_at timestamptz NOT NULL DEFAULT now(),
 started_at timestamptz NOT NULL DEFAULT now(),
 stopped_at timestamptz,
 stop_reason text,
 CHECK(stopped_at IS NULL OR stopped_at >= started_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS fleet_one_active_tracking_session
 ON fleet_tracking_sessions(trip_id) WHERE stopped_at IS NULL;

-- Finance: invoices remain separate from received payments so every balance
-- and reconciliation decision is auditable.
CREATE TABLE IF NOT EXISTS invoices (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 facility_id uuid NOT NULL REFERENCES facilities(id),
 invoice_number text NOT NULL UNIQUE,
 issue_date date NOT NULL DEFAULT CURRENT_DATE,
 due_date date NOT NULL,
 status text NOT NULL DEFAULT 'issued' CHECK(status IN ('draft','issued','part_paid','paid','overdue','void')),
 currency text NOT NULL DEFAULT 'UGX',
 subtotal numeric(12,2) NOT NULL DEFAULT 0 CHECK(subtotal >= 0),
 amount_paid numeric(12,2) NOT NULL DEFAULT 0 CHECK(amount_paid >= 0),
 balance numeric(12,2) NOT NULL DEFAULT 0 CHECK(balance >= 0),
 notes text NOT NULL DEFAULT '',
 created_by_id uuid NOT NULL REFERENCES users(id),
 issued_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK(due_date >= issue_date)
);
CREATE INDEX IF NOT EXISTS invoices_facility_due ON invoices(facility_id,due_date DESC);
CREATE INDEX IF NOT EXISTS invoices_open_due ON invoices(due_date) WHERE status IN ('issued','part_paid','overdue');
CREATE TABLE IF NOT EXISTS invoice_lines (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 invoice_id uuid NOT NULL REFERENCES invoices(id),
 description text NOT NULL,
 quantity numeric(12,3) NOT NULL CHECK(quantity > 0),
 unit_price numeric(12,2) NOT NULL CHECK(unit_price >= 0),
 line_total numeric(12,2) NOT NULL CHECK(line_total >= 0),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS invoice_lines_invoice ON invoice_lines(invoice_id);
CREATE TABLE IF NOT EXISTS payment_allocations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 payment_id uuid NOT NULL REFERENCES payments(id),
 invoice_id uuid NOT NULL REFERENCES invoices(id),
 amount numeric(12,2) NOT NULL CHECK(amount > 0),
 allocated_by_id uuid NOT NULL REFERENCES users(id),
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(payment_id,invoice_id)
);
CREATE INDEX IF NOT EXISTS payment_allocations_invoice ON payment_allocations(invoice_id);

-- SMS outbox. The application records every planned and attempted message;
-- delivery uses an explicitly configured provider and is never faked.
CREATE TABLE IF NOT EXISTS sms_reminders (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 reminder_key text NOT NULL UNIQUE,
 facility_id uuid NOT NULL REFERENCES facilities(id),
 collection_id uuid REFERENCES collections(id),
 invoice_id uuid REFERENCES invoices(id),
 kind text NOT NULL CHECK(kind IN ('upcoming_collection','overdue_balance')),
 recipient_phone text NOT NULL,
 message text NOT NULL,
 scheduled_for timestamptz NOT NULL,
 status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','sent','failed','skipped')),
 provider_reference text,
 last_error text,
 sent_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sms_reminders_pending ON sms_reminders(scheduled_for) WHERE status='queued';

-- Marketer field work. A visit has a server-assigned plan, a phone GPS
-- check-in, submitted client notes and a supervisor review trail.
CREATE TABLE IF NOT EXISTS marketing_visits (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 marketer_id uuid NOT NULL REFERENCES users(id),
 facility_id uuid REFERENCES facilities(id),
 planned_by_id uuid NOT NULL REFERENCES users(id),
 client_name text NOT NULL,
 client_phone text NOT NULL DEFAULT '',
 address text NOT NULL DEFAULT '',
 planned_for timestamptz NOT NULL,
 status text NOT NULL DEFAULT 'scheduled' CHECK(status IN ('scheduled','checked_in','submitted','approved','returned','cancelled')),
 check_in_latitude double precision,
 check_in_longitude double precision,
 check_in_accuracy_m double precision,
 checked_in_at timestamptz,
 contact_name text NOT NULL DEFAULT '',
 contact_phone text NOT NULL DEFAULT '',
 outcome text NOT NULL DEFAULT '',
 notes text NOT NULL DEFAULT '',
 follow_up_on date,
 submitted_at timestamptz,
 reviewed_by_id uuid REFERENCES users(id),
 reviewed_at timestamptz,
 review_notes text NOT NULL DEFAULT '',
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK((check_in_latitude IS NULL AND check_in_longitude IS NULL AND check_in_accuracy_m IS NULL) OR
       (check_in_latitude BETWEEN -90 AND 90 AND check_in_longitude BETWEEN -180 AND 180 AND check_in_accuracy_m BETWEEN 0 AND 1000))
);
CREATE INDEX IF NOT EXISTS marketing_visits_marketer_schedule ON marketing_visits(marketer_id,planned_for DESC);
CREATE INDEX IF NOT EXISTS marketing_visits_status_schedule ON marketing_visits(status,planned_for DESC);

-- Existing deployments were created before the Marketer role was added.
-- Replacing only this CHECK constraint preserves every existing user record.
DO $$
BEGIN
 ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
 ALTER TABLE users ADD CONSTRAINT users_role_check
  CHECK(role IN ('Administrator','Supervisor','Waste Collector','Revenue Officer','Marketer'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
