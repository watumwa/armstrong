# Armstrong Global Solutions — Unified Platform

## Deployment model
**One Vercel Services project** rooted at this repository. The Next.js frontend is served at `/`; Django is the only public API service and is served at `/api/*`. Both services build, preview, deploy and roll back together on one domain. PostgreSQL remains an external managed database (for example Neon), not a separately deployed application server.

The browser uses relative `/api/...` calls, so it always reaches the Django service on the same origin. This avoids a hard-coded backend hostname and avoids CORS configuration for the web application. The older `frontend/src/app/api` route files are retained as rollback source only; the Vercel rewrite prevents public traffic from reaching them. Do not add new Next API handlers.

## Initial backend foundation (October 2026)
- Login via server-validated credentials; signed, HttpOnly, SameSite cookies.
- Administrator-only staff listing and account creation for Administrator, Supervisor, Waste Collector and Revenue Officer.
- PostgreSQL schema for users, facilities, agreements, collections, payments and audit logs.
- Authenticated facility directory and creation, GPS coordinate endpoint, collection scheduling API, pending payment recording API and database-backed report summary.
- Google Maps facility view at `/maps`: embedded map requires `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` and **verified** facility coordinates. Do not invent locations.
- `/users` staff provisioning interface; `/login` sign-in interface.
- Optional **fictional** demo seed at `db/demo_seed.sql`. It contains no real customer data and should not be run on production.

## One-project setup
1. In Vercel, change the existing project's **Root Directory** to `.` (the repository root) and set the framework preset to **Services**. Commit `vercel.json` before deploying; it defines the `frontend` and `backend` services and routes `/api/*` to Django before the frontend catch-all.
2. In that same Vercel project, configure `DATABASE_URL`, `AUTH_SECRET` (a unique 32+ character value), `DJANGO_SECRET_KEY` (a different unique 32+ character value), and `DJANGO_ALLOWED_HOSTS` (include your production domain plus `.vercel.app`). Both services receive the shared project environment. Do not commit secrets or set `ADMIN_PASSWORD` in Vercel.
3. Apply `frontend/db/schema.sql` to the database using its SQL editor before attempting to sign in. These tables are the current source of truth; the Django models deliberately use `managed=False`.
4. On a trusted computer, set `DATABASE_URL`, `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` (12+ characters), then run `cd frontend && npm install && node scripts/bootstrap-admin.mjs`. This creates the first administrator only when none exists.
5. Deploy from the repository root. With Git integration, every push builds both services once; with the CLI, use `vercel deploy` (preview) or `vercel deploy --prod` (production) from this directory.
6. Verify `GET /api/health`, then open `/login`, sign in and create other staff accounts at `/users`.
7. Optionally configure `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` in Vercel, restrict it to your website's HTTP referrers and enable the **Maps Embed API** in Google Cloud. GPS coordinates must be recorded/verified before facilities appear on the map.

## Current integration boundaries — important
This is a **backend foundation, not a finished production system**. The home dashboard now loads authenticated role information and facility records through Django from PostgreSQL; facility creation saves to the database. The Reports page uses Django server summary data. The dedicated collector, scheduling, QR, verification and agreement demo pages still use local state or browser storage and **are not yet connected to the database**. Dashboard payment and collection modal activity is still demo-only; do not use it to acknowledge actual cash or issue official receipts. The payment API creates *pending* records, never automatically confirmed payments. Facility payment badges on the home dashboard are placeholders until reconciliation is implemented. Role enforcement exists on implemented server endpoints; remaining workflows require endpoint-level authorization, validation and audit logging before production use.

## Deployment safety
No database connection or migrations have been executed remotely. No real customer data has been inserted. The login gate intentionally prevents access to operational pages until the database, administrator and authentication secret are configured. Build, migration and device tests are required before go-live.

## Frontend development
```bash
cd frontend
npm install
npm run dev
```

## Four-role test credentials
No real login passwords are stored in this repository. To create **temporary test accounts** in an **empty, non-production PostgreSQL database**, apply the schema first and run:

```bash
cd frontend
npm install
ALLOW_TEST_USERS=yes node scripts/create-test-users.mjs
```

Provide `DATABASE_URL` in your terminal environment before running the command. The script creates one account each for Administrator, Supervisor, Waste Collector and Revenue Officer, with unique randomly generated passwords printed **once** to the terminal. Save them in a password manager. The script refuses to run in `NODE_ENV=production` or when any user already exists. For a real deployment, create only the initial administrator using `scripts/bootstrap-admin.mjs`, then create staff through `/users`.
