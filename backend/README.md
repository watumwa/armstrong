# Armstrong Django API (integration in progress)

Django REST Framework models map to the existing `frontend/db/schema.sql` PostgreSQL tables. Models intentionally use `managed=False`: **do not run Django migrations expecting them to create these tables**. The existing SQL schema is the current source of truth; migration to Django-managed migrations needs an explicit data-preserving plan.

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
Authentication reads the existing Next.js `armstrong_session` JWT cookie using the **same AUTH_SECRET**. Django routes: `/v1/facilities/`, `/v1/agreements/`, `/v1/collections/`, `/v1/payments/`, `/v1/users/`, `/v1/reports/summary/`. Mutations enforce roles and record audit actions. Collector submission and supervisor verification are supported.

**Not yet deployed as a Vercel Python function.** The current Vercel project has a Next.js root at `frontend/`, and a sibling `backend/` folder is outside that build root. Simply adding Django does not make it run on the same deployment. A tested monorepo root/build configuration and serverless function routing are required before switching frontend requests to Django. Existing Next API routes remain active meanwhile. Do not claim these Django routes are live.

Do not store medical patient data in this system. Validate privacy, collection chain-of-custody and statutory retention requirements before production.
