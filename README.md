# Armstrong Global Solutions — Waste Management Platform

## Architecture

- **Frontend:** Next.js App Router, React, TypeScript, Tailwind CSS, Lucide icons.
- **Backend (later phase):** Django + Django REST Framework.
- **Database (later phase):** PostgreSQL.

## Run the frontend

```bash
git clone https://github.com/watumwa/armstrong.git
cd armstrong/frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Current features

Responsive operations dashboard, facility directory and registration, demo collections and payments, staff preview, schedules and agreement listing, reporting, and role-based UI previews. Dedicated routes: `/agreements/new` (three-step printable agreement draft) and `/qr-registry` (printable QR sticker preview and separate collection/payment demo forms), and `/schedules` (collector assignments, filters, status updates and workload summaries), and `/collector` (mobile task queue and unverified collection evidence submissions), and `/verification` (supervisor review, demo approval and correction requests).

## Critical limitations

This is a **frontend-only demonstration**. All data is illustrative and resets on refresh. Role switching is **not authorization**. QR stickers encode demo client IDs, not secure credentials. There is no real QR scanning, GPS verification, payment processing, ledger, invoices, backend, or persistent storage. The map intentionally does not invent facility coordinates.

The `backend/` Django project will be added only when backend development is approved.

## Git workflow

Per project instructions, completed changes are committed directly to `main`.

**Workflow limitation:** Collector and supervisor pages currently use independent illustrative datasets. A collector's new submission will not appear in the supervisor queue until shared backend storage and APIs are implemented.
