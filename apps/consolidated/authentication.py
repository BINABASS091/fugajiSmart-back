import datetime
from django.conf import settings
from django.middleware import csrf
from django.http import JsonResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Authentication class that reads the JWT access token from an HttpOnly cookie
    defined by SIMPLE_JWT['AUTH_COOKIE'] when Authorization header is absent.
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

def set_jwt_cookies(response, request, access_token, refresh_token=None):
    # Access token cookie
    response.set_cookie(
        key=settings.SIMPLE_JWT['AUTH_COOKIE'],
        value=access_token,
        expires=datetime.datetime.utcnow() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
        secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly=True,
        samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'],
    )
    # Refresh token cookie (optional)
    if refresh_token:
        response.set_cookie(
            key=settings.SIMPLE_JWT.get('REFRESH_COOKIE', 'refresh_token'),
            value=refresh_token,
            expires=datetime.datetime.utcnow() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
            secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
            httponly=True,
            samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
            path=settings.SIMPLE_JWT.get('REFRESH_COOKIE_PATH', '/api/v1/auth/refresh/'),
        )
    # Ensure CSRF cookie is present
    csrf_token = csrf.get_token(request)
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        secure=settings.CSRF_COOKIE_SECURE,
        samesite=settings.CSRF_COOKIE_SAMESITE,
        path='/',
    )
    return response

class CookieTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return JsonResponse(
                {"detail": "Invalid credentials"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        response = JsonResponse(serializer.validated_data, status=status.HTTP_200_OK)
        return set_jwt_cookies(
            response,
            request,
            serializer.validated_data['access'],
            serializer.validated_data['refresh']
        )

class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['REFRESH_COOKIE'])
        
        if not refresh_token:
            return JsonResponse(
                {"detail": "No refresh token found in cookies"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        # Validate the refresh token
        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            
            response = JsonResponse({
                'access': access_token,
                'refresh': str(refresh)
            }, status=status.HTTP_200_OK)
            
            return set_jwt_cookies(response, request, access_token, str(refresh))
            
        except Exception as e:
            return JsonResponse(
                {"detail": "Invalid or expired refresh token"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

class CookieTokenLogoutView(APIView):
    def post(self, request, *args, **kwargs):
        response = JsonResponse({'detail': 'logged out'}, status=status.HTTP_200_OK)
        response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE'], path=settings.SIMPLE_JWT['AUTH_COOKIE_PATH'])
        response.delete_cookie(
            settings.SIMPLE_JWT.get('REFRESH_COOKIE', 'refresh_token'),
            path=settings.SIMPLE_JWT.get('REFRESH_COOKIE_PATH', '/api/v1/auth/refresh/')
        )
        return response
