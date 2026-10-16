import os
from pathlib import Path
import dj_database_url
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.environ.get("DJANGO_SECRET_KEY") or os.environ.get("AUTH_SECRET")
if not SECRET_KEY or len(SECRET_KEY)<32: raise RuntimeError("Set DJANGO_SECRET_KEY or AUTH_SECRET to 32+ characters")
DEBUG=os.environ.get("DJANGO_DEBUG","false").lower()=="true"
ALLOWED_HOSTS=[h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS",".vercel.app,localhost,127.0.0.1").split(",") if h.strip()]
INSTALLED_APPS=["django.contrib.auth","django.contrib.contenttypes","rest_framework","corsheaders","operations"]
MIDDLEWARE=["django.middleware.security.SecurityMiddleware","corsheaders.middleware.CorsMiddleware","django.middleware.common.CommonMiddleware"]
ROOT_URLCONF="core.urls"
DATABASES={"default":dj_database_url.config(default=os.environ.get("DATABASE_URL"),conn_max_age=0,ssl_require=not DEBUG)}
if not os.environ.get("DATABASE_URL"):raise RuntimeError("DATABASE_URL required")
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
USE_TZ=True
TIME_ZONE="Africa/Kampala"
REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES":["operations.authentication.ArmstrongSessionAuthentication"],"DEFAULT_PERMISSION_CLASSES":["rest_framework.permissions.IsAuthenticated"],"DEFAULT_PAGINATION_CLASS":"rest_framework.pagination.PageNumberPagination","PAGE_SIZE":50}
CORS_ALLOWED_ORIGINS=[x for x in os.environ.get("CORS_ALLOWED_ORIGINS","").split(",") if x]
SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
