import os
from urllib.parse import urlsplit

import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from .models import StaffUser


class ArmstrongSessionAuthentication(BaseAuthentication):
    """Authenticate the shared HttpOnly session cookie issued by Django."""

    def authenticate(self, request):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("Origin")
            if not origin:
                raise PermissionDenied("Origin header required for state-changing requests")

            if urlsplit(origin).netloc != request.get_host():
                raise PermissionDenied("Cross-origin write requests are not allowed")

        token = request.COOKIES.get("armstrong_session")
        if not token:
            return None

        secret = os.environ.get("AUTH_SECRET")
        if not secret:
            raise AuthenticationFailed("Authentication not configured")

        try:
            data = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
            user = StaffUser.objects.get(pk=data["sub"], active=True)
            return (user, None)
        except (jwt.PyJWTError, StaffUser.DoesNotExist, ValueError):
            raise AuthenticationFailed("Invalid session")
