# Armstrong Django API

Django REST Framework models map to the PostgreSQL tables defined in `schema.sql`. Models intentionally use `managed=False`: **do not run Django migrations expecting them to create these tables**. Vercel runs `scripts/apply_schema.py` at backend build time; its DDL is idempotent and does not seed or delete application data. Keep this schema aligned with `frontend/db/schema.sql`, the frontend's local bootstrap copy.

Vercel Services deploys this Django application and the Next.js frontend together from the repository root. `vercel.json` sends every `/api/*` request to Django, while all other paths go to Next.js. The public API stays on the same domain as the browser and owns login, logout, session validation, facilities, users, collections, payments and reports.

## Local development
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# export DATABASE_URL, AUTH_SECRET, DJANGO_SECRET_KEY
python manage.py check
python manage.py runserver 127.0.0.1:8000
```
Authentication uses the HttpOnly `armstrong_session` JWT issued by Django with the shared **AUTH_SECRET**. Frontend-compatible endpoints are `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`, `/api/facilities`, `/api/users`, `/api/collections`, `/api/payments`, `/api/reports/summary`, and `/api/health`. Mutations enforce roles and record audit actions. The existing `/v1/` REST routes remain available for Django-native integrations, including collector submission and supervisor verification.

To deploy, point the Vercel project at the repository root (`.`), select the **Services** framework preset, set the shared environment variables, and deploy normally. Do not point the project at `frontend/`; that would omit this service. Vercel Services is currently a beta feature, so use a preview deployment to verify `/api/health` and `/login` before promoting production.

Do not store medical patient data in this system. Validate privacy, collection chain-of-custody and statutory retention requirements before production.
