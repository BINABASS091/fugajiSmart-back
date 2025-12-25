"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

# Use the app-level views/authentication rather than a non-existent config module
from apps.consolidated.authentication import (
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CookieTokenLogoutView,
)
from apps.consolidated.views import (
    RegisterView,
    UserProfileView,
    FarmViewSet,
    BatchViewSet,
    DeviceViewSet,
    ActivityViewSet,
    AlertViewSet,
    RecommendationViewSet,
    SubscriptionViewSet,
    HealthViewSet,
)

router = DefaultRouter()
router.register(r'farms', FarmViewSet, basename='farm')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'activities', ActivityViewSet, basename='activity')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'recommendations', RecommendationViewSet, basename='recommendation')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'health', HealthViewSet, basename='health')


@ensure_csrf_cookie
def csrf_view(request):
    return JsonResponse({'detail': 'CSRF cookie set'})


urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),

    # API routes (URLPathVersioning)
    path('api/<str:version>/', include('apps.consolidated.urls')),
    
    # AI routes (no version needed)
    path('api/v1/ai/', include('apps.ai.urls')),

    path('', include(router.urls)),

    # API schema & docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Auth routes
    path('auth/csrf/', csrf_view, name='csrf'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/profile/', UserProfileView.as_view(), name='profile'),
    path('auth/login/', CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', CookieTokenLogoutView.as_view(), name='token_logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
