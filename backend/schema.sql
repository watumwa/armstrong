-- This build-time copy lets the Django service bootstrap its Neon schema.
-- Keep it aligned with frontend/db/schema.sql, the frontend's local bootstrap file.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS users(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),name text NOT NULL,email text NOT NULL UNIQUE,role text NOT NULL CHECK(role IN ('Administrator','Supervisor','Waste Collector','Revenue Officer')),password_hash text NOT NULL,active boolean NOT NULL DEFAULT true,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS facilities(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),code text NOT NULL UNIQUE,name text NOT NULL,type text NOT NULL,address text NOT NULL,district text NOT NULL DEFAULT 'Kampala',phone text NOT NULL,latitude double precision,longitude double precision,monthly_fee numeric(12,2) NOT NULL DEFAULT 0 CHECK(monthly_fee>=0),collection_day text,created_at timestamptz NOT NULL DEFAULT now(),CHECK(latitude BETWEEN -90 AND 90),CHECK(longitude BETWEEN -180 AND 180));
CREATE TABLE IF NOT EXISTS agreements(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),facility_id uuid NOT NULL REFERENCES facilities(id),reference text UNIQUE NOT NULL,status text NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','active','expired','terminated')),start_date date,end_date date,monthly_fee numeric(12,2) NOT NULL CHECK(monthly_fee>=0),created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS collections(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),facility_id uuid NOT NULL REFERENCES facilities(id),collector_id uuid REFERENCES users(id),scheduled_at timestamptz NOT NULL,status text NOT NULL DEFAULT 'scheduled' CHECK(status IN ('scheduled','en_route','arrived','submitted','verified','rejected','missed')),waste_category text,bags integer CHECK(bags>=0),weight_kg numeric(12,3) CHECK(weight_kg>=0),notes text,verified_by uuid REFERENCES users(id),verified_at timestamptz,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS payments(id uuid PRIMARY KEY DEFAULT gen_random_uuid(),facility_id uuid NOT NULL REFERENCES facilities(id),received_by uuid REFERENCES users(id),amount numeric(12,2) NOT NULL CHECK(amount>0),method text NOT NULL,reference text UNIQUE NOT NULL,status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','confirmed','void')),paid_at timestamptz NOT NULL DEFAULT now(),created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS audit_log(id bigserial PRIMARY KEY,actor_id uuid REFERENCES users(id),action text NOT NULL,entity_type text NOT NULL,entity_id text NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_collections_facility_date ON collections(facility_id,scheduled_at DESC);
CREATE INDEX IF NOT EXISTS idx_payments_facility_date ON payments(facility_id,paid_at DESC);

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
