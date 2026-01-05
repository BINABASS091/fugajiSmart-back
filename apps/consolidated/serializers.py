from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils import timezone
from django.db.models import Count, Max
from drf_spectacular.utils import extend_schema_field
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
    Payment,
    SubscriptionPlan,
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


# Base Inventory Serializers
class InventoryItemSerializer(serializers.ModelSerializer):
    farmer_id = serializers.UUIDField(source='farmer.id', read_only=True)
    farm_id = serializers.UUIDField(source='farm.id', read_only=True, allow_null=True)
    batch_id = serializers.UUIDField(source='batch.id', read_only=True, allow_null=True)
    
    # Computed fields for professional inventory management
    days_to_expiry = serializers.SerializerMethodField()
    is_near_expiry = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    shelf_life_remaining_percentage = serializers.SerializerMethodField()
    should_reorder = serializers.SerializerMethodField()
    calculated_order_quantity = serializers.SerializerMethodField()
    inventory_status = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    market_value = serializers.SerializerMethodField()
    quality_impact_factor = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'farmer_id']
        extra_kwargs = {
            'farmer': {'write_only': True, 'required': False},
            'farm': {'write_only': True, 'required': False},
            'batch': {'write_only': True, 'required': False},
        }
    
    def get_days_to_expiry(self, obj):
        return obj.get_days_to_expiry()
    
    def get_is_near_expiry(self, obj):
        return obj.is_near_expiry()
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_shelf_life_remaining_percentage(self, obj):
        return obj.get_shelf_life_remaining_percentage()
    
    def get_should_reorder(self, obj):
        return obj.should_reorder()
    
    def get_calculated_order_quantity(self, obj):
        return obj.calculate_order_quantity()
    
    def get_inventory_status(self, obj):
        return obj.get_inventory_status()
    
    def get_total_cost(self, obj):
        return obj.calculate_total_cost()
    
    def get_market_value(self, obj):
        return obj.calculate_market_value()
    
    def get_quality_impact_factor(self, obj):
        return obj.get_quality_impact_factor()
    
    def validate_category(self, value):
        """Validate category is in allowed choices"""
        valid_categories = [choice[0] for choice in InventoryItem.CATEGORY_CHOICES]
        if value not in valid_categories:
            raise serializers.ValidationError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
        return value
    
    def validate_subcategory(self, value):
        """Validate subcategory if provided"""
        if value:
            valid_subcategories = [choice[0] for choice in InventoryItem.SUBCATEGORY_CHOICES]
            if value not in valid_subcategories:
                raise serializers.ValidationError(f"Invalid subcategory. Must be one of: {', '.join(valid_subcategories)}")
        return value

class InventoryTransactionSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True, allow_null=True)
    batch_id = serializers.UUIDField(source='batch.id', read_only=True, allow_null=True)
    
    class Meta:
        model = InventoryTransaction
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'total_cost', 'batch_id', 'batch_number']
        extra_kwargs = {
            'batch': {'write_only': True, 'required': False},
        }

    def create(self, validated_data):
        # Calculate total cost if unit cost is provided
        if 'unit_cost' in validated_data and 'quantity_change' in validated_data:
            validated_data['total_cost'] = validated_data['unit_cost'] * validated_data['quantity_change']
        return super().create(validated_data)

class FeedConsumptionSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    batch_id = serializers.UUIDField(source='batch.id', read_only=True)
    item_name = serializers.CharField(source='inventory_item.name', read_only=True)
    item_id = serializers.UUIDField(source='inventory_item.id', read_only=True)
    
    class Meta:
        model = FeedConsumption
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'batch_id', 'item_id']
        extra_kwargs = {
            'batch': {'write_only': True, 'required': False},
            'inventory_item': {'write_only': True, 'required': False},
        }

class InventoryAlertSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    
    class Meta:
        model = InventoryAlert
        fields = '__all__'

# Specialized Inventory Serializers

class MedicineInventorySerializer(serializers.ModelSerializer):
    inventory_item_details = InventoryItemSerializer(source='inventory_item', read_only=True)
    
    class Meta:
        model = MedicineInventory
        fields = '__all__'

class MedicineAdministrationSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.inventory_item.name', read_only=True)
    batch_name = serializers.CharField(source='batch.batch_name', read_only=True)
    administered_by_name = serializers.CharField(source='administered_by.get_full_name', read_only=True)
    
    class Meta:
        model = MedicineAdministration
        fields = '__all__'

class EquipmentInventorySerializer(serializers.ModelSerializer):
    inventory_item_details = InventoryItemSerializer(source='inventory_item', read_only=True)
    
    class Meta:
        model = EquipmentInventory
        fields = '__all__'

class LaborRecordSerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source='farmer.business_name', read_only=True)
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    
    class Meta:
        model = LaborRecord
        fields = '__all__'

class ServiceExpenseSerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source='farmer.business_name', read_only=True)
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    
    class Meta:
        model = ServiceExpense
        fields = '__all__'

class HealthRecordSerializer(serializers.ModelSerializer):
    batch_number = serializers.CharField(source='affected_batch.batch_number', read_only=True)
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    
    class Meta:
        model = HealthRecord
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'farm_name', 'batch_number']
        extra_kwargs = {
            'farm': {'write_only': True, 'required': True},
            'affected_batch': {'write_only': True, 'required': False},
            'reported_by': {'write_only': True, 'required': False}
        }

class HealthAlertSerializer(serializers.ModelSerializer):
    batch_name = serializers.CharField(source='batch.batch_name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.get_full_name', read_only=True)
    
    class Meta:
        model = HealthAlert
        fields = '__all__'

class EggInventorySerializer(serializers.ModelSerializer):
    batch_name = serializers.CharField(source='batch.batch_name', read_only=True)
    
    class Meta:
        model = EggInventory
        fields = '__all__'

class EggSaleSerializer(serializers.ModelSerializer):
    egg_inventory_details = EggInventorySerializer(source='egg_inventory', read_only=True)
    
    class Meta:
        model = EggSale
        fields = '__all__'


# Constants
DEVICE_TYPE_LABELS = {
    'TEMPERATURE_SENSOR': 'Temperature Sensor',
    'HUMIDITY_SENSOR': 'Humidity Sensor',
    'AIR_QUALITY': 'Air Quality Sensor',
    'WEIGHT_SCALE': 'Weight Scale',
    'FEEDER': 'Automatic Feeder',
    'WATERER': 'Automatic Waterer',
    'CAMERA': 'Surveillance Camera',
    'CONTROLLER': 'Environmental Controller',
    'OTHER': 'Other Device'
}

# Field length constants
MAX_NAME_LEN = 255
MAX_SERIAL_LEN = 100
MAX_NOTES_LEN = 2000
MAX_FW_LEN = 50


# Authentication Serializers
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'role', 'phone', 'first_name', 'last_name', 'full_name', 'preferred_currency', 'created_at')
        read_only_fields = ('id', 'created_at', 'full_name')
        extra_kwargs = {'password': {'write_only': True}}

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = get_user_model()
        fields = ('email', 'password', 'password2', 'role', 'phone')
        extra_kwargs = {
            'role': {'required': False, 'default': 'FARMER'},
            'phone': {'required': False}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2', None)
        # Default role to FARMER if not provided
        if not validated_data.get('role'):
            validated_data['role'] = 'FARMER'
        user = get_user_model().objects.create_user(**validated_data)
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data.update({
            'user': {
                'id': self.user.id,
                'email': self.user.email,
                'role': self.user.role,
            }
        })
        return data

# Model Serializers
class FarmerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    id = serializers.UUIDField(source='pk', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = FarmerProfile
        fields = ['id', 'user', 'business_name', 'location', 'experience_years', 'verification_status', 'avatar_url', 'created_at', 'updated_at']
        read_only_fields = ('created_at', 'updated_at')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_avatar_url(self, obj):
        try:
            if obj.avatar and hasattr(obj.avatar, 'url'):
                return obj.avatar.url
        except Exception:
            return None
        return None

class FarmMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = ['id', 'name']

class FarmSerializer(serializers.ModelSerializer):
    farmer = FarmerProfileSerializer(read_only=True)
    farmer_id = serializers.PrimaryKeyRelatedField(
        queryset=FarmerProfile.objects.all(),
        source='farmer',
        write_only=True,
        required=True,
        help_text="ID of the farmer who owns this farm"
    )
    
    class Meta:
        model = Farm
        fields = ['id', 'name', 'location', 'size_hectares', 'latitude', 'longitude', 
                  'status', 'farmer', 'farmer_id', 'created_at', 'updated_at']
        read_only_fields = ('created_at', 'updated_at', 'farmer')

class BatchSerializer(serializers.ModelSerializer):
    farm_id = serializers.UUIDField(source='farm.id', read_only=True)
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    farm = serializers.PrimaryKeyRelatedField(queryset=Farm.objects.all(), write_only=True)
    breed_config_id = serializers.PrimaryKeyRelatedField(
        queryset=BreedConfiguration.objects.all(),
        source='breed_config',
        write_only=True,
        required=False,
        allow_null=True,
        help_text="ID of the breed configuration (optional)"
    )

    class Meta:
        model = Batch
        fields = ['id', 'farm', 'farm_id', 'farm_name', 'batch_number', 'breed', 'breed_config_id',
                  'quantity', 'start_date', 'expected_end_date', 'status', 'mortality_count', 
                  'current_age_days', 'created_at', 'updated_at']
        read_only_fields = ('created_at', 'updated_at', 'farm_id', 'farm_name')

class BreedConfigurationSerializer(serializers.ModelSerializer):
    breed_type_display = serializers.CharField(source='get_breed_type_display', read_only=True)
    recommended_housing_system_display = serializers.CharField(source='get_recommended_housing_system_display', read_only=True)
    
    class Meta:
        model = BreedConfiguration
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'breed_type_display', 'recommended_housing_system_display')

    def validate_breed_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Breed name cannot be empty.")
        return value.strip()
    
    def validate_average_weight_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError("Average weight must be greater than zero.")
        return value

class BreedStageSerializer(serializers.ModelSerializer):
    breed_name = serializers.CharField(source='breed.breed_name', read_only=True)
    
    class Meta:
        model = BreedStage
        fields = [
            'id', 'breed', 'breed_name', 'stage_name', 'description', 'start_day', 
            'end_day', 'feeding_guide', 'health_tips', 'housing_requirements',
            'expected_weight_kg', 'mortality_threshold_percent', 'feed_type',
            'vaccination_schedule', 'common_diseases', 'management_practices',
            'order_index', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, data):
        if data['start_day'] >= data['end_day']:
            raise serializers.ValidationError("End day must be after start day.")
        
        # Check for overlapping stages
        overlapping = BreedStage.objects.filter(
            breed=data.get('breed'),
            start_day__lte=data['end_day'],
            end_day__gte=data['start_day']
        )
        
        if self.instance:  # For updates, exclude current instance
            overlapping = overlapping.exclude(id=self.instance.id)
            
        if overlapping.exists():
            raise serializers.ValidationError("This stage overlaps with an existing stage.")
            
        return data

class BreedMilestoneSerializer(serializers.ModelSerializer):
    breed_name = serializers.CharField(source='breed.breed_name', read_only=True)
    stage_name = serializers.CharField(source='stage.stage_name', read_only=True, allow_null=True)
    
    class Meta:
        model = BreedMilestone
        fields = [
            'id', 'breed', 'breed_name', 'stage', 'stage_name', 'milestone_day',
            'milestone_title', 'milestone_description', 'action_required',
            'is_critical', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_milestone_day(self, value):
        if value < 0:
            raise serializers.ValidationError("Milestone day cannot be negative.")
        return value
    
    def validate(self, data):
        stage = data.get('stage')
        milestone_day = data.get('milestone_day')
        
        if stage and milestone_day:
            if not (stage.start_day <= milestone_day <= stage.end_day):
                raise serializers.ValidationError(
                    f"Milestone day must be between stage start day ({stage.start_day}) "
                    f"and end day ({stage.end_day})."
                )
                
        return data

class DeviceSerializer(serializers.ModelSerializer):
    """
    Serializer for Device model providing nested farm & batch plus validation.
    """
    farm = FarmMinimalSerializer(read_only=True)
    batch = serializers.SerializerMethodField()
    device_type_label = serializers.SerializerMethodField()
    # Write-only fields to accept foreign keys from the API
    farm_id = serializers.PrimaryKeyRelatedField(
        queryset=Farm.objects.all(), source='farm', write_only=True
    )
    batch_id = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(), source='batch', allow_null=True, required=False, write_only=True
    )

    class Meta:
        model = Device
        fields = [
            'id',
            'device_name',
            'serial_number',
            'device_type',
            'device_type_label',
            'status',
            'farm',
            'farm_id',
            'batch',
            'batch_id',
            'firmware_version',
            'installation_date',
            'last_online',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_online', 'farm', 'batch', 'device_type_label']
        extra_kwargs = {
            'batch_id': {'required': False, 'allow_null': True},
            'notes': {'required': False, 'allow_null': True},
            'firmware_version': {'required': False, 'allow_null': True},
        }

    @extend_schema_field(serializers.CharField())
    def get_device_type_label(self, obj):
        return DEVICE_TYPE_LABELS.get(obj.device_type, obj.device_type)

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_batch(self, obj):
        batch = getattr(obj, 'batch', None)
        if batch:
            return {'id': str(batch.id), 'batch_number': getattr(batch, 'batch_number', None) or getattr(batch, 'name', '')}
        return None

    def validate_device_name(self, value: str):
        v = value.strip()
        if not v:
            raise serializers.ValidationError("Device name cannot be blank.")
        if len(v) > MAX_NAME_LEN:
            raise serializers.ValidationError(f"Device name too long (>{MAX_NAME_LEN}).")
        return v

    def validate_serial_number(self, value: str):
        v = value.strip()
        if not v:
            raise serializers.ValidationError("Serial number cannot be blank.")
        if len(v) > MAX_SERIAL_LEN:
            raise serializers.ValidationError(f"Serial number too long (>{MAX_SERIAL_LEN}).")
        return v

    def validate_device_type(self, value: str):
        v = value.strip().upper()
        if v not in DEVICE_TYPE_LABELS:
            raise serializers.ValidationError(f"Invalid device_type. Allowed: {', '.join(sorted(DEVICE_TYPE_LABELS.keys()))}")
        return v

    def validate_status(self, value: str):
        allowed = {'ACTIVE', 'INACTIVE', 'MAINTENANCE', 'FAULTY', 'ERROR', 'ONLINE', 'OFFLINE'}
        v = value.strip().upper()
        if v not in allowed:
            raise serializers.ValidationError(f"Invalid status. Allowed: {', '.join(sorted(allowed))}")
        return v

    def validate_firmware_version(self, value: str):
        if value is None:
            return None
        v = value.strip()
        if not v:
            return None
        if len(v) > MAX_FW_LEN:
            raise serializers.ValidationError(f"Firmware version too long (>{MAX_FW_LEN}).")
        return v

    def validate_notes(self, value: str):
        if value is None:
            return None
        v = value.strip()
        if len(v) > MAX_NOTES_LEN:
            raise serializers.ValidationError(f"Notes too long (>{MAX_NOTES_LEN}).")
        return v

    def validate(self, attrs):
        # Ensure serial number is unique
        if 'serial_number' in attrs:
            qs = Device.objects.filter(
                serial_number__iexact=attrs['serial_number']
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError({
                    'serial_number': 'A device with this serial number already exists.'
                })

        # Validate installation date is not in the future
        if 'installation_date' in attrs and attrs['installation_date'] > timezone.now().date():
            raise ValidationError({
                'installation_date': 'Installation date cannot be in the future.'
            })

        # Ensure device type-specific validations
        device_type = attrs.get('device_type', getattr(self.instance, 'device_type', None))
        if device_type == 'CAMERA' and not attrs.get('firmware_version'):
            raise ValidationError({
                'firmware_version': 'Firmware version is required for camera devices.'
            })

        return attrs

# Activity, Alert, and Recommendation Serializers
class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = '__all__'
        read_only_fields = ('created_at',)

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = '__all__'
        read_only_fields = ('created_at',)

class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = '__all__'
        read_only_fields = ('created_at',)

# Subscription Related Serializers
class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'description', 'price', 'duration_days',
            'max_farms', 'max_devices', 'features', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value
    
    def validate_duration_days(self, value):
        if value <= 0:
            raise serializers.ValidationError("Duration must be at least 1 day.")
        return value
    
    def validate_features(self, value):
        required_features = [
            'can_add_farm', 'can_add_batch', 'can_add_inventory',
            'can_view_analytics', 'can_export_data', 'can_use_api'
        ]
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Features must be a JSON object.")
            
        for feature in required_features:
            if feature not in value:
                value[feature] = False
                
        return value
        read_only_fields = ('created_at', 'updated_at')

class SubscriptionSerializer(serializers.ModelSerializer):
    days_remaining = serializers.SerializerMethodField()
    # Provide nested plan details from the FK 'plan'
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id', 'farmer', 'plan', 'plan_details', 'status', 'start_date',
            'end_date', 'amount', 'is_active', 'auto_renew', 'trial_ends_at',
            'cancelled_at', 'cancellation_reason', 'notes', 'days_remaining',
            'created_at', 'updated_at'
        ]
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'days_remaining',
            'trial_ends_at', 'cancelled_at', 'end_date', 'amount'
        )

    @extend_schema_field(serializers.CharField())
    def get_days_remaining(self, obj):
        if obj.end_date:
            delta = obj.end_date - timezone.now().date()
            return str(max(0, delta.days))
        return None
    
    def validate(self, data):
        if self.instance and 'status' in data:
            current_status = self.instance.status
            new_status = data['status']
            
            if current_status == 'CANCELLED' and new_status != current_status:
                raise serializers.ValidationError(
                    "A cancelled subscription cannot be reactivated. Please create a new subscription."
                )
                
        return data
    
    def create(self, validated_data):
        # Set default end date if not provided
        if 'end_date' not in validated_data and 'plan' in validated_data:
            plan = validated_data['plan']
            validated_data['end_date'] = timezone.now().date() + timezone.timedelta(days=plan.duration_days)
            
            # Set trial period for free plans
            if plan.price == 0 and 'trial_ends_at' not in validated_data:
                validated_data['trial_ends_at'] = timezone.now().date() + timezone.timedelta(days=7)
                
        return super().create(validated_data)
        read_only_fields = ('created_at', 'updated_at')

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class UserFeatureAccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFeatureAccess
        fields = [
            'id', 'user', 'can_add_farm', 'can_add_batch', 'can_add_inventory',
            'can_view_analytics', 'can_export_data', 'can_use_api', 'max_farms',
            'max_batches_per_farm', 'max_devices', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_max_farms(self, value):
        if value < 0:
            raise serializers.ValidationError("Max farms cannot be negative.")
        return value
    
    def validate_max_batches_per_farm(self, value):
        if value < 0:
            raise serializers.ValidationError("Max batches per farm cannot be negative.")
        return value
    
    def validate_max_devices(self, value):
        if value < 0:
            raise serializers.ValidationError("Max devices cannot be negative.")
        return value
    
    def update(self, instance, validated_data):
        # Prevent reducing limits below current usage
        if 'max_farms' in validated_data:
            farm_count = Farm.objects.filter(farmer__user=instance.user).count()
            if validated_data['max_farms'] < farm_count:
                raise serializers.ValidationError(
                    f"Cannot set max_farms below current farm count ({farm_count})."
                )
                
        if 'max_batches_per_farm' in validated_data:
            max_batches = Farm.objects.filter(farmer__user=instance.user)\
                .annotate(batch_count=Count('batches'))\
                .aggregate(max_batches=Max('batch_count'))['max_batches'] or 0
                
            if validated_data['max_batches_per_farm'] < max_batches:
                raise serializers.ValidationError(
                    f"Cannot set max_batches_per_farm below current maximum batches per farm ({max_batches})."
                )
                
        if 'max_devices' in validated_data:
            device_count = Device.objects.filter(farm__farmer__user=instance.user).count()
            if validated_data['max_devices'] < device_count:
                raise serializers.ValidationError(
                    f"Cannot set max_devices below current device count ({device_count})."
                )
                
        return super().update(instance, validated_data)
        read_only_fields = ('created_at', 'updated_at')

# Nested/Detail Serializers
class FarmDetailSerializer(FarmSerializer):
    batches = BatchSerializer(many=True, read_only=True)
    
    class Meta(FarmSerializer.Meta):
        fields = '__all__'

class BatchDetailSerializer(BatchSerializer):
    activities = ActivitySerializer(many=True, read_only=True)
    
    class Meta(BatchSerializer.Meta):
        fields = BatchSerializer.Meta.fields + ['activities']

# View Serializers
class UserProfileSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()
    role = serializers.CharField()
    phone = serializers.CharField()
    farmer_profile = serializers.SerializerMethodField()
    business_name = serializers.CharField(source='farmer_profile.business_name', required=False)
    location = serializers.CharField(source='farmer_profile.location', required=False)
    experience_years = serializers.IntegerField(source='farmer_profile.experience_years', required=False)
    verification_status = serializers.CharField(source='farmer_profile.verification_status', required=False)
    avatar_url = serializers.SerializerMethodField()
    def get_farmer_profile(self, obj):
        fp = getattr(obj, 'farmer_profile', None)
        if fp:
            return {
                'id': str(fp.id),
                'business_name': getattr(fp, 'business_name', None),
                'location': getattr(fp, 'location', None),
                'experience_years': getattr(fp, 'experience_years', None),
                'verification_status': getattr(fp, 'verification_status', None),
                'avatar_url': self.get_avatar_url(obj),
            }
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_avatar_url(self, obj):
        fp = getattr(obj, 'farmer_profile', None)
        try:
            if fp and fp.avatar and hasattr(fp.avatar, 'url'):
                return fp.avatar.url
        except Exception:
            return None
        return None

    def update(self, instance, validated_data):
        farmer_profile_data = validated_data.pop('farmer_profile', {})
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update or create farmer profile
        farmer_profile = instance.farmer_profile
        if farmer_profile_data:
            for attr, value in farmer_profile_data.items():
                setattr(farmer_profile, attr, value)
            farmer_profile.save()
            
        return instance

