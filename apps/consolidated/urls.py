from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .authentication import (
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CookieTokenLogoutView,
)
from .views import (
    RegisterView,
    UserProfileView,
    UserAvatarUploadView,
    FarmViewSet,
    BatchViewSet,
    DeviceViewSet,
    BreedConfigurationViewSet,
    BreedStageViewSet,
    BreedMilestoneViewSet,
    ActivityViewSet,
    AlertViewSet,
    RecommendationViewSet,
    SubscriptionViewSet,
    HealthViewSet,
    GoogleLoginView,
    FarmerViewSet,
    InventoryItemViewSet,
    InventoryTransactionViewSet,
)

router = DefaultRouter()
router.register(r'farmers', FarmerViewSet, basename='farmer')
router.register(r'farms', FarmViewSet, basename='farm')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'breedconfigurations', BreedConfigurationViewSet, basename='breedconfiguration')
router.register(r'breedstages', BreedStageViewSet, basename='breedstage')
router.register(r'breedmilestones', BreedMilestoneViewSet, basename='breedmilestone')
router.register(r'activities', ActivityViewSet, basename='activity')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'recommendations', RecommendationViewSet, basename='recommendation')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'health', HealthViewSet, basename='health')
router.register(r'inventory', InventoryItemViewSet, basename='inventory-item')
router.register(r'inventory-transactions', InventoryTransactionViewSet, basename='inventory-transaction')

@ensure_csrf_cookie
def csrf_view(request, version=None):
    return JsonResponse({'detail': 'CSRF cookie set'})

urlpatterns = [
    path('auth/csrf/', csrf_view, name='csrf'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/profile/', UserProfileView.as_view(), name='profile'),
    path('auth/profile/avatar/', UserAvatarUploadView.as_view(), name='profile_avatar'),
    path('auth/login/', CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/google/', GoogleLoginView.as_view(), name='google_login'),
    path('auth/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', CookieTokenLogoutView.as_view(), name='token_logout'),
    path('', include(router.urls)),
]