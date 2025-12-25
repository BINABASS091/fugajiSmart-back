from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Lightweight authentication class that prefers the JWT access token from the
    HttpOnly cookie defined by SIMPLE_JWT['AUTH_COOKIE'] when the Authorization
    header is missing. Keeps imports minimal to avoid DRF circular imports during
    settings initialization.
    """
    def authenticate(self, request):
        # Try standard Authorization header first
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            # Fallback to cookie
            cookie_name = settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token')
            raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
