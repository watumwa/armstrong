# Armstrong Global Solutions — Unified Platform

## Deployment model
**One Vercel project** pointing at the `frontend/` directory. The Next.js application serves both UI and server-side API routes at the **same origin** (`/api/*`). PostgreSQL is an external managed database (e.g. Neon). There is **no separately deployed Django service** in this architecture. The earlier Django plan has been superseded to meet the single-deployment requirement.

## Initial backend foundation (October 2026)
- Login via server-validated credentials; signed, HttpOnly, SameSite cookies.
- Administrator-only staff listing and account creation for Administrator, Supervisor, Waste Collector and Revenue Officer.
- PostgreSQL schema for users, facilities, agreements, collections, payments and audit logs.
- Authenticated facility directory and creation, GPS coordinate endpoint, collection scheduling API, pending payment recording API and database-backed report summary.
- Google Maps facility view at `/maps`: embedded map requires `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` and **verified** facility coordinates. Do not invent locations.
- `/users` staff provisioning interface; `/login` sign-in interface.
- Optional **fictional** demo seed at `db/demo_seed.sql`. It contains no real customer data and should not be run on production.

## One-project setup
1. In Vercel, set **Root Directory = `frontend`**. Build command `npm run build`; framework Next.js. One project serves both pages and API routes.
2. Provision a PostgreSQL database and set `DATABASE_URL` and a unique `AUTH_SECRET` (32+ characters) in the **same Vercel project**. See `frontend/.env.example`. Do not commit secrets.
3. Apply `frontend/db/schema.sql` to the database using your SQL editor before attempting to sign in.
4. On a trusted computer, set `DATABASE_URL`, `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` (12+ characters), then run `cd frontend && npm install && node scripts/bootstrap-admin.mjs`. This creates the first administrator only when none exists. Do not leave the bootstrap password in deployed environment variables.
5. Redeploy, open `/login`, sign in and create other staff accounts at `/users`.
6. Optionally configure `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` in Vercel, restrict it to your website's HTTP referrers and enable the **Maps Embed API** in Google Cloud. GPS coordinates must be recorded/verified before facilities appear on the map.

## Current integration boundaries — important
This is a **backend foundation, not a finished production system**. The home dashboard now loads authenticated role information and facility records from PostgreSQL; facility creation saves to the database. The Reports page uses server summary data. The dedicated collector, scheduling, QR, verification and agreement demo pages still use local state or browser storage and **are not yet connected to the database**. Dashboard payment and collection modal activity is still demo-only; do not use it to acknowledge actual cash or issue official receipts. The payment API creates *pending* records, never automatically confirmed payments. Facility payment badges on the home dashboard are placeholders until reconciliation is implemented. Role enforcement exists on implemented server endpoints; remaining workflows require endpoint-level authorization, validation and audit logging before production use.

## Deployment safety
No database connection or migrations have been executed remotely. No real customer data has been inserted. The login gate intentionally prevents access to operational pages until the database, administrator and authentication secret are configured. Build, migration and device tests are required before go-live.

## Frontend development
```bash
cd frontend
npm install
npm run dev
```
