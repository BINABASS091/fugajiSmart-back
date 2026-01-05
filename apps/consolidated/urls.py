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
    GoogleLoginView,
    FarmerViewSet,
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
    InventoryItemViewSet,
    InventoryTransactionViewSet,
    FeedConsumptionViewSet,
    InventoryAlertViewSet,
    HealthRecordViewSet,
    MedicineInventoryViewSet,
    MedicineAdministrationViewSet,
    EquipmentInventoryViewSet,
    LaborRecordViewSet,
    ServiceExpenseViewSet,
    HealthAlertViewSet,
    EggInventoryViewSet,
    EggSaleViewSet,
)
from .views_currency import update_currency_preference
from apps.consolidated.views_professional_inventory import (
    batch_inventory_summary,
    professional_inventory_analytics,
    optimize_inventory_policy
)
from apps.consolidated.views_performance_hub import (
    performance_hub_dashboard,
    get_performance_trends
)
from apps.consolidated.views_metrics_logging import (
    log_flock_weights,
    log_survival_metrics,
    report_losses
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
router.register(r'feed-consumption', FeedConsumptionViewSet, basename='feed-consumption')
router.register(r'inventory-alerts', InventoryAlertViewSet, basename='inventory-alert')
router.register(r'health-records', HealthRecordViewSet, basename='health-record')
router.register(r'medicine-inventory', MedicineInventoryViewSet, basename='medicine-inventory')
router.register(r'medicine-administration', MedicineAdministrationViewSet, basename='medicine-administration')
router.register(r'equipment-inventory', EquipmentInventoryViewSet, basename='equipment-inventory')
router.register(r'labor-records', LaborRecordViewSet, basename='labor-record')
router.register(r'service-expenses', ServiceExpenseViewSet, basename='service-expense')
router.register(r'health-alerts', HealthAlertViewSet, basename='health-alert')
router.register(r'egg-inventory', EggInventoryViewSet, basename='egg-inventory')
router.register(r'egg-sales', EggSaleViewSet, basename='egg-sale')


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
    path('auth/currency/', update_currency_preference, name='update_currency'),
    
    # Professional Inventory Management
    path('inventory/batch/<uuid:batch_id>/summary/', batch_inventory_summary, name='batch_inventory_summary'),
    path('inventory/analytics/', professional_inventory_analytics, name='professional_inventory_analytics'),
    path('inventory/optimize/', optimize_inventory_policy, name='optimize_inventory_policy'),
    
    # Performance Hub
    path('performance/hub/', performance_hub_dashboard, name='performance_hub_dashboard'),
    path('performance/batch/<uuid:batch_id>/trends/', get_performance_trends, name='get_performance_trends'),
    
    # Metrics Logging
    path('metrics/log-weights/', log_flock_weights, name='log_flock_weights'),
    path('metrics/log-survival/', log_survival_metrics, name='log_survival_metrics'),
    path('metrics/report-losses/', report_losses, name='report_losses'),
    
    path('', include(router.urls)),
]