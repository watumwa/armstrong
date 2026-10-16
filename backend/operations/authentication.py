import os
import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import StaffUser
class ArmstrongSessionAuthentication(BaseAuthentication):
 def authenticate(self,request):
  token=request.COOKIES.get("armstrong_session")
  if not token:return None
  secret=os.environ.get("AUTH_SECRET")
  if not secret:raise AuthenticationFailed("Authentication not configured")
  try:
   data=jwt.decode(token,secret,algorithms=["HS256"],options={"require":["exp","sub"]})
   user=StaffUser.objects.get(pk=data["sub"],active=True)
   return (user,None)
  except (jwt.PyJWTError,StaffUser.DoesNotExist,ValueError):
   raise AuthenticationFailed("Invalid session")
