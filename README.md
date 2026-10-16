# Armstrong Waste Management — Frontend

Responsive React + TypeScript + Vite prototype for Armstrong Global Solutions SMC Ltd.

## Start locally

Requires Node.js 20+.

```bash
git clone https://github.com/watumwa/armstrong.git
cd armstrong
npm install
npm run dev
```

Visit the Vite URL printed in the terminal (typically http://localhost:5173).

Production build:

```bash
npm run build
```

## Frontend features

- Responsive navy and green management dashboard
- Facilities directory, search, CSV export and temporary client registration
- Service agreement, collection schedule and QR registry previews
- Collection and payment demonstration forms
- Field-role preview switcher (administrator, supervisor, waste collector, revenue officer)
- Staff roster, account reporting, client details and activity history
- Map registry placeholder that **does not invent GPS coordinates**

## Important limitations

**This is a frontend-only demonstration.** All facilities and staff are fictional examples. Data is in memory and resets on refresh. No authenticated access, secure QR scanner, GPS verification, payment processing, legal receipts, persistent storage, or backend exists yet. Payment status is illustrative and is not a financial ledger.

The role switcher is for visual preview only and **does not enforce permissions**. Do not use this system to handle real clinical waste or money until backend authorization, auditing, validation and production workflows are implemented.

## Delivery

All frontend changes are committed to `main` as requested. Backend implementation is deferred.

## Next frontend iterations

Add dedicated agreement wizard, QR print preview, detailed collection manifests, payment allocation and invoice screens, responsive route scheduling, component tests, and realistic empty/error/loading states.
