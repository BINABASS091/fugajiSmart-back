from rest_framework import viewsets, permissions, mixins, status, views
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q, Count, Sum, Avg
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiParameter
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    FarmerProfileSerializer,
    UserProfileSerializer,
    FarmSerializer,
    BatchSerializer,
    BatchDetailSerializer,
    BreedConfigurationSerializer,
    BreedStageSerializer,
    BreedMilestoneSerializer,
    InventoryItemSerializer,
    InventoryTransactionSerializer,
    FeedConsumptionSerializer,
    InventoryAlertSerializer,
    ActivitySerializer,
    AlertSerializer,
    RecommendationSerializer,
    DeviceSerializer,
    SubscriptionSerializer,
    HealthRecordSerializer,
    MedicineInventorySerializer,
    MedicineAdministrationSerializer,
    EquipmentInventorySerializer,
    LaborRecordSerializer,
    ServiceExpenseSerializer,
    HealthAlertSerializer,
    EggInventorySerializer,
    EggSaleSerializer,
)
from .api_docs import (
    extend_schema_auth, 
    REGISTER_EXAMPLES, 
    LOGIN_EXAMPLES, 
    FARM_EXAMPLES,
    USER_EXAMPLE,
    extend_schema_list,
    AUTH_ERROR_RESPONSE,
    PAGINATION_PARAMETERS
)

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
import requests
import os
from django.contrib.auth import get_user_model
User = get_user_model()
from .models import (
    FarmerProfile,
    Farm,
    Batch,
    BreedConfiguration,
    BreedStage,
    BreedMilestone,
    Device,
    Activity,
    Alert,
    Recommendation,
    Subscription,
    UserFeatureAccess,
    InventoryItem,
    InventoryTransaction,
    FeedConsumption,
    InventoryAlert,
    HealthRecord,
    MedicineInventory,
    MedicineAdministration,
    EquipmentInventory,
    LaborRecord,
    ServiceExpense,
    HealthAlert,
    EggInventory,
    EggSale,
)
from .authentication import set_jwt_cookies

class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'No token provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify Access Token via Google UserInfo API
            user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            resp = requests.get(user_info_url, params={'access_token': token})
            
            if resp.status_code != 200:
                print(f"Google Auth Error: {resp.text}")
                return Response({'error': 'Invalid Google token'}, status=status.HTTP_400_BAD_REQUEST)
            
            id_info = resp.json()
            
            if 'email' not in id_info:
                return Response({'error': 'Invalid token: email not found'}, status=status.HTTP_400_BAD_REQUEST)

            email = id_info['email']
            first_name = id_info.get('given_name', '')
            last_name = id_info.get('family_name', '')
            
            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': 'FARMER', # Default to FARMER
                    'is_active': True
                }
            )
            
            if created:
                user.set_unusable_password()
                user.save()
                # Create farmer profile
                if hasattr(user, 'role') and user.role == 'FARMER':
                     if not hasattr(user, 'farmer_profile'):
                        from .models import FarmerProfile
                        FarmerProfile.objects.create(user=user)

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            data = {
                'access': access_token,
                'refresh': refresh_token,
                'user': UserSerializer(user).data
            }
            
            response = Response(data)
            
            # Set cookies
            set_jwt_cookies(response, request, access_token, refresh_token)
            
            return response

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Custom Permissions
class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user

class IsFarmOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow farm owners to edit their farms and related objects.
    Staff users can manage any object.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Staff users can manage any object
        if request.user.is_staff:
            return True
        
        # Get user's farmer profile safely
        try:
            user_profile = request.user.farmer_profile
        except AttributeError:
            # User doesn't have a farmer_profile
            return False
        
        # Handle different model types
        if hasattr(obj, 'farmer'):
            # Direct farmer relationship (e.g., Activity)
            return obj.farmer == user_profile
        elif hasattr(obj, 'farm'):
            # Farm relationship (e.g., Device, Batch)
            return obj.farm.farmer == user_profile
        elif hasattr(obj, 'user'):
            # Direct user relationship
            return obj.user == request.user
        else:
            # Fallback for other objects
            return False

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit objects.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

@extend_schema_auth(
    summary='Register a new user',
    description='Creates a new user account with the provided credentials.',
    examples=REGISTER_EXAMPLES,
    responses={
        status.HTTP_201_CREATED: {
            'type': 'object',
            'properties': {
                'email': {'type': 'string'},
                'role': {'type': 'string'},
                'phone': {'type': 'string'}
            },
            'example': {
                'email': 'newfarmer@example.com',
                'role': 'FARMER',
                'phone': '+254712345679'
            }
        }
    }
)
class RegisterView(APIView):
    permission_classes = [AllowAny]  # Changed from AllowPermissions
    
    def post(self, request, version=None, *args, **kwargs):
        # Now you can access version if needed
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Create farmer profile for new users
            if user.role == 'FARMER':
                FarmerProfile.objects.create(user=user)
            return Response(RegisterSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema_auth(
    summary='Obtain JWT token',
    description='Authenticate user and obtain JWT access and refresh tokens.',
    examples=LOGIN_EXAMPLES,
    responses={
        status.HTTP_200_OK: {
            'type': 'object',
            'properties': {
                'access': {'type': 'string'},
                'refresh': {'type': 'string'},
                'user': {'type': 'object'}
            }
        }
    }
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@extend_schema_auth(
    summary='Get user profile',
    description='Retrieve the profile of the currently authenticated user.',
    responses={
        status.HTTP_200_OK: {
            'type': 'object',
            'properties': {
                'email': {'type': 'string'},
                'role': {'type': 'string'},
                'phone': {'type': 'string'},
                'farmer_profile': {'type': 'object'}
            },
            'example': USER_EXAMPLE
        }
    },
    methods=['GET']
)
@extend_schema_auth(
    summary='Update user profile',
    description='Update the profile of the currently authenticated user.',
    methods=['PATCH']
)
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get(self, request, version=None):
        """Get current user profile"""
        serializer = UserProfileSerializer({
            'id': request.user.id,
            'email': request.user.email,
            'role': request.user.role,
            'phone': request.user.phone,
            'farmer_profile': getattr(request.user, 'farmer_profile', None)
        })
        return Response(serializer.data)

    def patch(self, request, version=None):
        """Update user profile"""
        serializer = UserProfileSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            user = request.user
            user.email = serializer.validated_data.get('email', user.email)
            user.phone = serializer.validated_data.get('phone', user.phone)
            user.save()
            
            if hasattr(user, 'farmer_profile'):
                profile = user.farmer_profile
                profile.business_name = serializer.validated_data.get('business_name', profile.business_name)
                profile.location = serializer.validated_data.get('location', profile.location)
                profile.experience_years = serializer.validated_data.get('experience_years', profile.experience_years)
                profile.save()
            
            return Response(UserProfileSerializer({
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'phone': user.phone,
                'farmer_profile': getattr(user, 'farmer_profile', None)
            }).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, version=None):
        user = request.user
        if not hasattr(user, 'farmer_profile'):
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
        profile = user.farmer_profile

        avatar_file = request.data.get('avatar') or request.FILES.get('avatar')
        if not avatar_file:
            return Response({'error': 'No avatar file provided'}, status=status.HTTP_400_BAD_REQUEST)

        profile.avatar = avatar_file
        profile.save()

        data = {
            'avatar_url': getattr(profile.avatar, 'url', None)
        }
        return Response(data, status=status.HTTP_200_OK)

class FarmerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows farmers to be viewed (Admin only ideally).
    """
    queryset = FarmerProfile.objects.all().select_related('user')
    serializer_class = FarmerProfileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'business_name']
    ordering_fields = ['created_at', 'verification_status']

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def verify(self, request, pk=None):
        """
        Verify or reject a farmer profile.
        Only admin users can perform this action.
        """
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can verify farmer profiles'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        farmer = self.get_object()
        new_status = request.data.get('status', 'VERIFIED')
        
        if new_status not in ['VERIFIED', 'REJECTED', 'SUSPENDED']:
            return Response(
                {'error': 'Invalid status. Must be VERIFIED, REJECTED, or SUSPENDED'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        farmer.verification_status = new_status
        farmer.save()
        
        serializer = self.get_serializer(farmer)
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema_list(
        summary='List farms',
        description='List all farms accessible to the current user.'
    ),
    create=extend_schema(
        summary='Create farm',
        description='Create a new farm.',
        examples=FARM_EXAMPLES,
        responses={
            status.HTTP_201_CREATED: FarmSerializer,
            **AUTH_ERROR_RESPONSE
        }
    ),
    retrieve=extend_schema(
        summary='Retrieve farm',
        description='Retrieve details of a specific farm.',
        responses={
            status.HTTP_200_OK: FarmSerializer,
            status.HTTP_404_NOT_FOUND: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string', 'example': 'Not found.'}
                }
            },
            **AUTH_ERROR_RESPONSE
        }
    ),
    update=extend_schema(
        summary='Update farm',
        description='Update an existing farm.',
        responses={
            status.HTTP_200_OK: FarmSerializer,
            **AUTH_ERROR_RESPONSE
        }
    ),
    partial_update=extend_schema(
        summary='Partially update farm',
        description='Partially update an existing farm.',
        responses={
            status.HTTP_200_OK: FarmSerializer,
            **AUTH_ERROR_RESPONSE
        }
    ),
    destroy=extend_schema(
        summary='Delete farm',
        description='Delete a farm.',
        responses={
            status.HTTP_204_NO_CONTENT: None,
            **AUTH_ERROR_RESPONSE
        }
    )
)
class FarmViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows farms to be viewed or edited.
    Admins can create farms for any farmer; regular users can only create for themselves.
    """
    serializer_class = FarmSerializer
    permission_classes = [IsAuthenticated, IsFarmOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'location', 'farmer__user__email']
    ordering_fields = ['created_at', 'updated_at', 'name']
    filterset_fields = ['status', 'farmer']

    def get_queryset(self):
        # Handle schema generation (AnonymousUser) safely
        if getattr(self, "swagger_fake_view", False):
            return Farm.objects.none()
        if self.request.user.is_staff:
            return Farm.objects.all().select_related('farmer__user')
        return Farm.objects.filter(farmer=self.request.user.farmer_profile).select_related('farmer__user')

    def perform_create(self, serializer):
        # Admins can specify any farmer; regular users default to their own profile
        if self.request.user.is_staff and 'farmer' in serializer.validated_data:
            serializer.save()
        else:
            serializer.save(farmer=self.request.user.farmer_profile)
    
    def perform_update(self, serializer):
        # Admins can change farmer; regular users can only update their own farms
        if self.request.user.is_staff and 'farmer' in serializer.validated_data:
            serializer.save()
        else:
            serializer.save()

class BatchViewSet(viewsets.ModelViewSet):
    serializer_class = BatchDetailSerializer
    permission_classes = [IsAuthenticated, IsFarmOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['batch_number', 'breed', 'farm__name', 'farm__farmer__user__email']
    ordering_fields = ['start_date', 'created_at', 'updated_at']
    filterset_fields = ['farm', 'status', 'breed']

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Batch.objects.none()
        queryset = Batch.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(farm__farmer=self.request.user.farmer_profile)
        return queryset.select_related('farm__farmer__user', 'breed_config')

    def get_serializer_class(self):
        if self.action == 'list':
            return BatchSerializer
        return BatchDetailSerializer
    
    def perform_create(self, serializer):
        # Admins can specify any farm; regular users can only create in their own farms
        if self.request.user.is_staff and 'farm' in serializer.validated_data:
            serializer.save()
        else:
            # Validate that regular users only create in their own farms
            farm = serializer.validated_data.get('farm')
            if farm and farm.farmer != self.request.user.farmer_profile:
                raise serializers.ValidationError("You can only create batches in your own farms.")
            serializer.save()

class DeviceViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated, IsFarmOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['device_name', 'serial_number', 'device_type']
    ordering_fields = ['created_at', 'updated_at', 'last_online']
    filterset_fields = ['farm', 'batch', 'device_type', 'status']

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Device.objects.none()
        queryset = Device.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(farm__farmer=self.request.user.farmer_profile)
        return queryset.select_related('farm', 'batch')

    def perform_create(self, serializer):
        # Accept farm_id and batch_id from frontend
        farm_id = self.request.data.get('farm') or self.request.data.get('farm_id')
        batch_id = self.request.data.get('batch') or self.request.data.get('batch_id')
        if farm_id and not self.request.user.is_staff:
            farm = Farm.objects.filter(id=farm_id, farmer=self.request.user.farmer_profile).first()
            if not farm:
                raise serializers.ValidationError({"farm_id": "Invalid or unauthorized farm ID"})
        # Let serializer handle mapping farm_id/batch_id (write-only fields) to model FKs
        serializer.save()


class BreedConfigurationViewSet(viewsets.ModelViewSet):
    serializer_class = BreedConfigurationSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['breed_name', 'breed_type', 'description']
    ordering_fields = ['breed_name', 'created_at', 'updated_at']
    filterset_fields = ['breed_type', 'is_active']

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return BreedConfiguration.objects.none()
        return BreedConfiguration.objects.all()


class BreedStageViewSet(viewsets.ModelViewSet):
    serializer_class = BreedStageSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['breed']
    ordering_fields = ['order_index', 'start_day', 'end_day', 'created_at']

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return BreedStage.objects.none()
        return BreedStage.objects.select_related('breed')


class BreedMilestoneViewSet(viewsets.ModelViewSet):
    serializer_class = BreedMilestoneSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['breed', 'stage', 'is_critical']
    ordering_fields = ['milestone_day', 'created_at']

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return BreedMilestone.objects.none()
        return BreedMilestone.objects.select_related('breed', 'stage')

class ActivityViewSet(viewsets.ModelViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated, IsFarmOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # Remove non-model fields (e.g., 'priority') from filterset_fields
    filterset_fields = ['activity_type', 'status', 'scheduled_date', 'batch', 'farmer']
    search_fields = ['description']
    # If 'priority' is a computed field, allow ordering but do not filter by it
    ordering_fields = ['scheduled_date', 'completed_at', 'id']

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Activity.objects.none()
        queryset = Activity.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(batch__farm__farmer=self.request.user.farmer_profile)
        return queryset.select_related('batch', 'batch__farm')

    def perform_create(self, serializer):
        # Ensure the batch belongs to the current user's farm
        batch_id = self.request.data.get('batch')
        if batch_id and not self.request.user.is_staff:
            batch = Batch.objects.filter(
                id=batch_id, 
                farm__farmer=self.request.user.farmer_profile
            ).first()
            if not batch:
                raise serializers.ValidationError("Invalid batch ID")
        serializer.save()

class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated, IsFarmOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['message', 'alert_type', 'severity']
    ordering_fields = ['created_at', 'severity', 'id']
    filterset_fields = ['alert_type', 'severity', 'is_read']

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Alert.objects.none()
        queryset = Alert.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(farmer=self.request.user.farmer_profile)
            )
        return queryset.select_related('farmer')

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            serializer.save(farmer=self.request.user.farmer_profile)
        else:
            serializer.save()

class RecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RecommendationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'category', 'breed']
    ordering_fields = ['created_at', 'id']
    filterset_fields = ['category', 'breed', 'age_range_days']

    def get_queryset(self):
        # Remove is_active (not a field in model). Return all.
        if getattr(self, "swagger_fake_view", False):
            return Recommendation.objects.none()
        return Recommendation.objects.all()

class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows subscriptions to be viewed or edited.
    """
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['plan__name', 'status']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    filterset_fields = ['status', 'is_active', 'auto_renew']
    
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Subscription.objects.none()
        # Regular users can only see their own subscriptions
        if not self.request.user.is_staff:
            return Subscription.objects.filter(farmer__user=self.request.user)
        return Subscription.objects.all()
    
    def perform_create(self, serializer):
        # Set the farmer to the current user's farmer profile
        farmer = self.request.user.farmer_profile
        serializer.save(farmer=farmer)
        
        # Update user's feature access
        user_access, _ = UserFeatureAccess.objects.get_or_create(user=self.request.user)
        user_access.update_from_subscription(serializer.instance)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel an active subscription.
        """
        subscription = self.get_object()
        if subscription.status == 'CANCELLED':
            return Response(
                {'detail': 'Subscription is already cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.status = 'CANCELLED'
        subscription.cancelled_at = timezone.now()
        subscription.is_active = False
        subscription.save(update_fields=['status', 'cancelled_at', 'is_active', 'updated_at'])
        return Response({'status': 'subscription cancelled'})
    
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """
        Reactivate a cancelled subscription.
        """
        subscription = self.get_object()
        if subscription.status != 'CANCELLED':
            return Response(
                {'detail': 'Only cancelled subscriptions can be reactivated.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.status = 'ACTIVE'
        subscription.is_active = True
        subscription.cancelled_at = None
        subscription.save(update_fields=['status', 'is_active', 'cancelled_at', 'updated_at'])
        return Response({'status': 'subscription reactivated'})

# Public read-only health endpoint
@extend_schema_view(
    ping=extend_schema(
        summary="Health ping",
        description="Simple public health check.",
        responses={200: OpenApiResponse(description="Service OK")},
    ),
    list=extend_schema(
        summary="Health info",
        description="Service status information.",
        responses={200: OpenApiResponse(description="Service OK")},
    ),
)
class HealthViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'], url_path='ping')
    def ping(self, request):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)

    def list(self, request):
        return Response({'service': 'amazing-kuku', 'status': 'ok'})
class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'subcategory', 'farm', 'is_iot_device', 'is_emergency_stock', 'requires_refrigeration']
    search_fields = ['name', 'category', 'subcategory', 'barcode', 'batch_number', 'location', 'supplier']
    ordering_fields = ['name', 'quantity', 'cost_per_unit', 'created_at', 'updated_at', 'expiry_date']
    ordering = ['-created_at']
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        queryset = InventoryItem.objects.select_related('farmer', 'farm', 'batch')
        
        if user.role == 'FARMER':
            queryset = queryset.filter(farmer__user=user)
        elif user.role == 'ADMIN':
            queryset = queryset.all()
        else:
            queryset = queryset.none()
        
        # Filter by farm if provided
        farm_id = self.request.query_params.get('farm')
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'FARMER':
            # Ensure farmer profile exists
            farmer_profile = get_object_or_404(FarmerProfile, user=user)
            data = serializer.validated_data
            
            # Handle farm assignment if provided
            farm_id = self.request.data.get('farm')
            if farm_id:
                try:
                    farm = Farm.objects.get(id=farm_id, farmer=farmer_profile)
                    data['farm'] = farm
                except Farm.DoesNotExist:
                    pass
            
            # Handle batch assignment if provided
            batch_id = self.request.data.get('batch')
            if batch_id:
                try:
                    batch = Batch.objects.get(id=batch_id, farm__farmer=farmer_profile)
                    data['batch'] = batch
                except Batch.DoesNotExist:
                    pass
            
            serializer.save(farmer=farmer_profile, **data)
        else:
            # For admin, might need to pass farmer ID in request
            serializer.save()

class InventoryTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['item', 'transaction_type']
    ordering_fields = ['transaction_date', 'created_at']
    ordering = ['-transaction_date', '-created_at']
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        queryset = InventoryTransaction.objects.select_related('item', 'item__farmer', 'item__farm')
        
        if user.role == 'FARMER':
            queryset = queryset.filter(item__farmer__user=user)
        elif user.role == 'ADMIN':
            queryset = queryset.all()
        else:
            queryset = queryset.none()
        
        # Filter by item if provided
        item_id = self.request.query_params.get('item')
        if item_id:
            queryset = queryset.filter(item_id=item_id)
        
        # Filter by batch if provided
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)
        
        return queryset

    def perform_create(self, serializer):
        """Handle batch assignment for transactions"""
        user = self.request.user
        data = serializer.validated_data
        
        # Handle batch assignment if provided
        batch_id = self.request.data.get('batch')
        if batch_id and user.role == 'FARMER':
            try:
                farmer_profile = get_object_or_404(FarmerProfile, user=user)
                batch = Batch.objects.get(id=batch_id, farm__farmer=farmer_profile)
                data['batch'] = batch
            except Batch.DoesNotExist:
                pass
        
        serializer.save(**data)


class FeedConsumptionViewSet(viewsets.ModelViewSet):
    serializer_class = FeedConsumptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['batch', 'inventory_item', 'date']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date', '-created_at']
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        queryset = FeedConsumption.objects.select_related('batch', 'batch__farm', 'inventory_item', 'transaction')
        
        if user.role == 'FARMER':
            queryset = queryset.filter(batch__farm__farmer__user=user)
        elif user.role == 'ADMIN':
            queryset = queryset.all()
        else:
            queryset = queryset.none()
        
        # Filter by batch if provided
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)
        
        # Filter by inventory item if provided
        item_id = self.request.query_params.get('inventory_item')
        if item_id:
            queryset = queryset.filter(inventory_item_id=item_id)
        
        return queryset

    def perform_create(self, serializer):
        """Ensure batch belongs to farmer"""
        # (This is handled in serializer.validate usually, or add logic here)
        pass

class HealthRecordViewSet(viewsets.ModelViewSet):
    serializer_class = HealthRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['record_type', 'affected_batch', 'outcome', 'farm']
    ordering_fields = ['date', 'created_at', 'cost']
    ordering = ['-date', '-created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = HealthRecord.objects.select_related('farm', 'affected_batch', 'reported_by')
        
        if user.role == 'FARMER':
            queryset = queryset.filter(farm__farmer__user=user)
        elif user.role == 'ADMIN':
            queryset = queryset.all()
        else:
            queryset = queryset.none()
            
        # Filter by batch if provided
        batch_id = self.request.query_params.get('batch')
        if batch_id:
            queryset = queryset.filter(affected_batch_id=batch_id)
            
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'FARMER':
            # Auto-assign farm and reporter
            profile = get_object_or_404(FarmerProfile, user=user)
            
            # If batch is provided, ensure it belongs to farmer
            batch_id = self.request.data.get('affected_batch')
            if batch_id:
                try:
                    batch = Batch.objects.get(id=batch_id, farm__farmer=profile)
                    serializer.save(reported_by=profile, affected_batch=batch)
                except Batch.DoesNotExist:
                     raise serializers.ValidationError({"affected_batch": "Invalid batch ID"})
            else:
                 serializer.save(reported_by=profile)
        else:
            serializer.save()
        user = self.request.user
        if user.role == 'FARMER':
            farmer_profile = get_object_or_404(FarmerProfile, user=user)
            batch = serializer.validated_data.get('batch')
            if batch and batch.farm.farmer != farmer_profile:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"batch": "Batch does not belong to your farm"})
        serializer.save()


class InventoryAlertViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['item', 'alert_type', 'severity', 'is_resolved']
    ordering_fields = ['created_at', 'severity']
    ordering = ['-created_at']
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        queryset = InventoryAlert.objects.select_related('item', 'item__farmer', 'resolved_by')
        
        if user.role == 'FARMER':
            queryset = queryset.filter(item__farmer__user=user)
        elif user.role == 'ADMIN':
            queryset = queryset.all()
        else:
            queryset = queryset.none()
        
        # Filter by resolved status if provided
        is_resolved = self.request.query_params.get('is_resolved')
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved.lower() == 'true')
        
        # Filter by alert type if provided
        alert_type = self.request.query_params.get('alert_type')
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        return queryset

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert"""
        alert = self.get_object()
        alert.resolve(user=request.user)
        serializer = self.get_serializer(alert)
        return Response(serializer.data)

# New Inventory ViewSets

class MedicineInventoryViewSet(viewsets.ModelViewSet):
    queryset = MedicineInventory.objects.all()
    serializer_class = MedicineInventorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['medicine_type', 'vaccine_type', 'administration_route']
    search_fields = ['inventory_item__name', 'purpose']

    def get_queryset(self):
        return self.queryset.filter(inventory_item__farmer__user=self.request.user)

class MedicineAdministrationViewSet(viewsets.ModelViewSet):
    queryset = MedicineAdministration.objects.all()
    serializer_class = MedicineAdministrationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['batch', 'medicine']

    def get_queryset(self):
        return self.queryset.filter(batch__farm__farmer__user=self.request.user)

class EquipmentInventoryViewSet(viewsets.ModelViewSet):
    queryset = EquipmentInventory.objects.all()
    serializer_class = EquipmentInventorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['equipment_type', 'condition']
    search_fields = ['inventory_item__name', 'serial_number']

    def get_queryset(self):
        return self.queryset.filter(inventory_item__farmer__user=self.request.user)

class LaborRecordViewSet(viewsets.ModelViewSet):
    queryset = LaborRecord.objects.all()
    serializer_class = LaborRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['worker_type', 'payment_frequency', 'is_active', 'farm']
    search_fields = ['worker_name', 'role']

    def get_queryset(self):
        return self.queryset.filter(farmer__user=self.request.user)

class ServiceExpenseViewSet(viewsets.ModelViewSet):
    queryset = ServiceExpense.objects.all()
    serializer_class = ServiceExpenseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['service_type', 'farm', 'service_date']
    search_fields = ['service_provider', 'description']

    def get_queryset(self):
        return self.queryset.filter(farmer__user=self.request.user)

class HealthAlertViewSet(viewsets.ModelViewSet):
    queryset = HealthAlert.objects.all()
    serializer_class = HealthAlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['batch', 'alert_type', 'severity', 'resolved']

    def get_queryset(self):
        return self.queryset.filter(batch__farm__farmer__user=self.request.user)

class EggInventoryViewSet(viewsets.ModelViewSet):
    queryset = EggInventory.objects.all()
    serializer_class = EggInventorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['batch', 'collection_date', 'grade', 'quality']

    def get_queryset(self):
        return self.queryset.filter(batch__farm__farmer__user=self.request.user)

class EggSaleViewSet(viewsets.ModelViewSet):
    queryset = EggSale.objects.all()
    serializer_class = EggSaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['customer_type', 'payment_status', 'sale_date']
    search_fields = ['customer_name', 'customer_phone', 'invoice_number']

    def get_queryset(self):
        return self.queryset.filter(egg_inventory__batch__farm__farmer__user=self.request.user)
