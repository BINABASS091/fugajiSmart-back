import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.db.models import F

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = [
        ('FARMER', 'Farmer'),
        ('ADMIN', 'Admin'),
        ('STAFF', 'Staff'),
        ('VIEWER', 'Viewer'),
    ]
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('TZS', 'Tanzanian Shilling'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='FARMER')
    phone = models.CharField(max_length=20, blank=True, null=True)
    preferred_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Remove username field and use email as the unique identifier
    username = None
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    def __str__(self):
        return self.email

class FarmerProfile(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile', primary_key=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    experience_years = models.PositiveIntegerField(default=0)
    verification_status = models.CharField(max_length=10, choices=VERIFICATION_STATUS_CHOICES, default='PENDING')
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s Profile"

class Farm(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='farms')
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    size_hectares = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Batch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=255)
    breed = models.CharField(max_length=255)
    breed_config = models.ForeignKey('BreedConfiguration', on_delete=models.SET_NULL, null=True, blank=True, related_name='batches', help_text="Associated breed configuration for this batch")
    quantity = models.IntegerField(default=0)
    start_date = models.DateField()
    expected_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='ACTIVE')
    mortality_count = models.IntegerField(default=0)
    current_age_days = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Batch {self.batch_number} - {self.status}"

class BreedConfiguration(models.Model):
    BREED_TYPE_CHOICES = [
        ('LAYER', 'Layer'),
        ('BROILER', 'Broiler'),
        ('DUAL_PURPOSE', 'Dual-Purpose/Hybrid'),
    ]
    
    HOUSING_SYSTEM_CHOICES = [
        ('CAGE', 'Cage System'),
        ('DEEP_LITTER', 'Deep Litter System'),
        ('FREE_RANGE', 'Free Range System'),
        ('SEMI_INTENSIVE', 'Semi-Intensive System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    breed_name = models.CharField(max_length=255, unique=True)
    breed_type = models.CharField(max_length=20, choices=BREED_TYPE_CHOICES)
    description = models.TextField(null=True, blank=True)
    
    # Basic Characteristics
    average_maturity_days = models.IntegerField(default=0, help_text="Days to reach maturity")
    production_lifespan_days = models.IntegerField(default=0, help_text="Total production lifespan in days")
    average_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Average adult weight in kg")
    
    # Layer-specific (if breed_type is LAYER)
    eggs_per_year = models.IntegerField(default=0, help_text="Expected eggs per year")
    onset_of_lay_weeks = models.IntegerField(null=True, blank=True, help_text="Age when laying begins (weeks)")
    laying_duration_weeks = models.IntegerField(null=True, blank=True, help_text="Laying duration in weeks")
    lighting_requirements_hours = models.IntegerField(null=True, blank=True, help_text="Required hours of light daily")
    feed_before_lay_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Feed consumption before point of lay (kg)")
    
    # Broiler-specific (if breed_type is BROILER)
    growth_rate_days = models.CharField(max_length=50, null=True, blank=True, help_text="Days to reach market weight (e.g., '28-42')")
    feed_conversion_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="FCR - Feed needed for 1kg weight gain")
    market_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Target market weight in kg")
    
    # Dual-Purpose/Hybrid specific
    egg_production_dual = models.IntegerField(null=True, blank=True, help_text="Eggs per year for dual-purpose")
    body_weight_dual_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Body weight at 16-18 weeks for dual-purpose")
    
    # Feeding
    feed_consumption_daily_grams = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Daily feed consumption in grams")
    
    # Housing & Space
    space_requirement_sqm = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Space requirement per bird in sqm")
    recommended_housing_system = models.CharField(max_length=20, choices=HOUSING_SYSTEM_CHOICES, null=True, blank=True, help_text="Best rearing system")
    suitability = models.TextField(null=True, blank=True, help_text="Suitability description")
    
    # Environment
    temperature_min_celsius = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Minimum temperature in Celsius")
    temperature_max_celsius = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Maximum temperature in Celsius")
    ideal_temperature_range = models.CharField(max_length=50, null=True, blank=True, help_text="Ideal temperature range (e.g., '20-24°C')")
    humidity_min_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Minimum humidity percentage")
    humidity_max_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Maximum humidity percentage")
    ideal_humidity_range = models.CharField(max_length=50, null=True, blank=True, help_text="Ideal humidity range (e.g., '60-80%')")
    
    # Breed Examples
    example_strains = models.TextField(null=True, blank=True, help_text="Example breeds/strains (comma-separated)")
    
    # Characteristics
    characteristics = models.TextField(null=True, blank=True, help_text="Detailed characteristics")
    hardiness = models.CharField(max_length=20, null=True, blank=True, help_text="Hardiness level: Low, Moderate, High")
    growth_speed = models.CharField(max_length=20, null=True, blank=True, help_text="Growth speed: Slow, Moderate, Very Fast")
    feed_efficiency = models.CharField(max_length=20, null=True, blank=True, help_text="Feed efficiency: High, Moderate")
    
    # Market Information
    market_age_weeks = models.CharField(max_length=50, null=True, blank=True, help_text="Market age in weeks")
    best_for = models.TextField(null=True, blank=True, help_text="Best suited for (commercial, rural, etc.)")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.breed_name
    
    class Meta:
        verbose_name = "Breed Configuration"
        verbose_name_plural = "Breed Configurations"
        ordering = ['breed_type', 'breed_name']

class BreedStage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    breed = models.ForeignKey(BreedConfiguration, on_delete=models.CASCADE, related_name='stages')
    stage_name = models.CharField(max_length=255)
    start_day = models.IntegerField(default=0)
    end_day = models.IntegerField(default=0)
    description = models.TextField(null=True, blank=True)
    feeding_guide = models.TextField(null=True, blank=True)
    health_tips = models.TextField(null=True, blank=True)
    housing_requirements = models.TextField(null=True, blank=True)
    expected_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mortality_threshold_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    feed_type = models.TextField(null=True, blank=True)
    vaccination_schedule = models.TextField(null=True, blank=True)
    common_diseases = models.TextField(null=True, blank=True)
    management_practices = models.TextField(null=True, blank=True)
    order_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.stage_name

class BreedMilestone(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    breed = models.ForeignKey(BreedConfiguration, on_delete=models.CASCADE, related_name='milestones')
    stage = models.ForeignKey(BreedStage, on_delete=models.SET_NULL, null=True, blank=True, related_name='milestones')
    milestone_day = models.IntegerField()
    milestone_title = models.CharField(max_length=255)
    milestone_description = models.TextField(null=True, blank=True)
    action_required = models.TextField(null=True, blank=True)
    is_critical = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.milestone_title

class Device(models.Model):
    DEVICE_TYPE_CHOICES = [
        ('TEMPERATURE_SENSOR', 'Temperature Sensor'),
        ('HUMIDITY_SENSOR', 'Humidity Sensor'),
        ('AIR_QUALITY', 'Air Quality Sensor'),
        ('WEIGHT_SCALE', 'Weight Scale'),
        ('FEEDER', 'Feeder'),
        ('WATERER', 'Waterer'),
        ('CAMERA', 'Camera'),
        ('CONTROLLER', 'Controller'),
        ('OTHER', 'Other'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('MAINTENANCE', 'Maintenance'),
        ('FAULTY', 'Faulty'),
        ('ERROR', 'Error'),
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_name = models.CharField(max_length=120, help_text="User-friendly name for the device.")
    serial_number = models.CharField(max_length=120, unique=True, help_text="Unique serial number of the device.")
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INACTIVE')
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='devices')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')  
    
    firmware_version = models.CharField(max_length=50, null=True, blank=True)
    installation_date = models.DateField(default=timezone.now)
    last_online = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.device_name} ({self.serial_number})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Device"
        verbose_name_plural = "Devices"

class Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, null=True, blank=True, related_name='activities', help_text="Farm where activity occurs")
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='activities')
    ACTIVITY_TYPES = [
        ('FEEDING', 'Feeding'),
        ('VACCINATION', 'Vaccination'),
        ('CLEANING', 'Cleaning'),
        ('INSPECTION', 'Inspection'),
        ('OTHER', 'Other'),
    ]
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField(null=True, blank=True)
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    scheduled_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Activity {self.activity_type} for batch {self.batch}"

class Alert(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='alerts')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts', help_text="Farm related to this alert")
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts', help_text="Batch related to this alert")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts', help_text="Device that triggered this alert")
    ALERT_TYPES = [
        ('HEALTH', 'Health'),
        ('ENVIRONMENT', 'Environment'),
        ('DEVICE', 'Device'),
        ('SYSTEM', 'System'),
    ]
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alert {self.alert_type} - {self.severity}"

class Recommendation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    CATEGORY_CHOICES = [
        ('FEEDING', 'Feeding'),
        ('HEALTH', 'Health'),
        ('ENVIRONMENT', 'Environment'),
        ('BIOSECURITY', 'Biosecurity'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    content = models.TextField()
    breed = models.CharField(max_length=255, null=True, blank=True)
    age_range_days = models.CharField(max_length=100, null=True, blank=True)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='recommendations', help_text="Farmer this recommendation is for")
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True, related_name='recommendations', help_text="Specific batch this recommendation applies to")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommendations')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    PAYMENT_METHODS = [
        ('MPESA', 'M-Pesa'),
        ('CARD', 'Credit/Debit Card'),
        ('BANK', 'Bank Transfer'),
        ('OTHER', 'Other'),
    ]
    
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    receipt_number = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.transaction_id or self.id} - {self.amount}"

    class Meta:
        ordering = ['-payment_date']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'


class SubscriptionPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(help_text="Duration of the subscription in days")
    max_farms = models.IntegerField(default=1, help_text="Maximum number of farms allowed")
    max_devices = models.IntegerField(default=5, help_text="Maximum number of devices allowed")
    features = models.JSONField(default=dict, help_text="JSON object containing features for this plan")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['price']
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'


class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    
    STATUS_CHOICES = [
        ('TRIAL', 'Trial'),
        ('ACTIVE', 'Active'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
        ('PAYMENT_PENDING', 'Payment Pending'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TRIAL')
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)
    trial_ends_at = models.DateField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Subscription {self.plan.name} for {self.farmer}"


class UserFeatureAccess(models.Model):
    """
    Tracks which features a user has access to based on their subscription.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feature_access'
    )
    
    # Feature flags
    can_add_farm = models.BooleanField(default=False)
    can_add_batch = models.BooleanField(default=True)
    can_add_inventory = models.BooleanField(default=True)
    can_view_analytics = models.BooleanField(default=False)
    can_export_data = models.BooleanField(default=False)
    can_use_api = models.BooleanField(default=False)
    max_farms = models.PositiveIntegerField(default=1)
    max_batches_per_farm = models.PositiveIntegerField(default=3)
    max_devices = models.PositiveIntegerField(default=2)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Feature Access'
        verbose_name_plural = 'User Feature Access'
    
    def __str__(self):
        return f"Feature Access for {self.user.email}"
    
    def update_from_subscription(self, subscription):
        """Update feature access based on subscription plan"""
        if not subscription or not subscription.plan:
            return
            
        plan = subscription.plan
        self.can_add_farm = plan.max_farms > 1
        self.can_view_analytics = True
        self.can_export_data = True
        self.can_use_api = plan.max_devices > 2
        self.max_farms = plan.max_farms
        self.max_batches_per_farm = 10 if plan.max_farms > 1 else 3
        self.max_devices = plan.max_devices
        self.save()
class InventoryItem(models.Model):
    # Main Categories
    CATEGORY_CHOICES = [
        ('LIVE_BIRDS', 'Live Bird Inventory'),
        ('FEED', 'Feed Inventory'),
        ('MEDICINE', 'Medicine & Veterinary Inventory'),
        ('SUPPLEMENTS', 'Supplements & Additives'),
        ('EGGS', 'Egg Production Inventory'),
        ('EQUIPMENT', 'Housing & Farm Equipment'),
        ('SANITATION', 'Farm Sanitation & Biosecurity'),
        ('UTILITIES', 'Utilities & Consumables'),
        ('STORAGE', 'Storage & Packaging'),
        ('TRANSPORT', 'Transport & Logistics'),
        ('LABOR', 'Labor & Operational Items'),
        ('SALES', 'Sales & Business Inventory'),
        ('EMERGENCY', 'Disease & Emergency Stock'),
        ('WATER', 'Water & Drinking System'),
        ('HATCHERY', 'Hatchery Inventory'),
        ('WASTE', 'Waste & By-Products'),
        ('MACHINERY', 'Machinery & Tools'),
        ('OFFICE', 'Office & Digital Inventory'),
        ('FINANCIAL', 'Financial & Records Inventory'),
    ]

    # Subcategories for better organization
    SUBCATEGORY_CHOICES = [
        # Live Birds
        ('DAY_OLD_CHICKS', 'Day-Old Chicks (DOC)'),
        ('GROWER_BIRDS', 'Grower Birds'),
        ('BROILERS', 'Broilers'),
        ('LAYERS', 'Layers'),
        ('BREEDERS', 'Breeders'),
        ('PULLETS', 'Pullets'),
        ('COCKERELS', 'Cockerels'),
        ('PARENT_STOCK', 'Parent Stock'),
        ('REPLACEMENT_STOCK', 'Replacement Stock'),
        # Feed - Enhanced with specific types
        ('COMPLETE_FEEDS', 'Complete Feeds'),
        ('FEED_INGREDIENTS', 'Feed Ingredients (Raw Materials)'),
        ('CHICK_STARTER_MASH', 'Chick Starter Mash'),
        ('GROWER_MASH', 'Grower Mash'),
        ('LAYER_MASH', 'Layer Mash'),
        ('FINISHER_FEED', 'Finisher Feed'),
        ('BROILER_CONCENTRATE', 'Broiler Concentrate'),
        ('PREMIX', 'Premix'),
        ('CRUSHED_MAIZE', 'Crushed Maize'),
        ('SOYA_MEAL', 'Soya Meal'),
        ('FISH_MEAL', 'Fish Meal'),
        # Medicine
        ('VACCINES', 'Vaccines'),
        ('DRUGS_TREATMENTS', 'Drugs & Treatments'),
        ('DISINFECTANTS', 'Disinfectants'),
        # Supplements
        ('SUPPLEMENTS', 'Supplements'),
        # Eggs
        ('EGG_TYPES', 'Egg Types'),
        ('EGG_PACKAGING', 'Egg Packaging'),
        # Equipment
        ('POULTRY_HOUSE_EQUIPMENT', 'Poultry House Equipment'),
        ('IOT_DEVICES', 'IoT & Smart Devices'),
        # Sanitation
        ('BIOSECURITY', 'Biosecurity Items'),
        ('SANITATION_TOOLS', 'Sanitation Tools'),
        # Utilities - Enhanced with specific types
        ('UTILITIES', 'Utilities'),
        ('CONSUMABLES', 'Consumables'),
        ('BEDDING', 'Bedding Materials (Sawdust, Rice Husks)'),
        ('LIME', 'Lime/Disinfectant Powder'),
        ('CLEANING_MATERIALS', 'Cleaning Materials'),
        ('FUEL', 'Fuel/Energy'),
        ('WATER_BILLS', 'Water Bills/Utilities'),
        ('ELECTRICITY', 'Electricity/Power'),
        # Storage
        ('PACKAGING', 'Packaging Materials'),
        ('STORAGE_EQUIPMENT', 'Storage Equipment'),
        # Transport
        ('TRANSPORT_EQUIPMENT', 'Transport Equipment'),
        ('TRANSPORT_CONSUMABLES', 'Transport Consumables'),
        # Labor
        ('LABOR_EQUIPMENT', 'Labor Equipment'),
        # Sales
        # Eggs
        ('EGG_TYPES', 'Egg Types'),
        ('EGG_PACKAGING', 'Egg Packaging'),
        # Equipment
        ('POULTRY_HOUSE_EQUIPMENT', 'Poultry House Equipment'),
        ('IOT_DEVICES', 'IoT & Smart Devices'),
        # Sanitation
        ('BIOSECURITY', 'Biosecurity Items'),
        ('SANITATION_TOOLS', 'Sanitation Tools'),
        # Utilities
        ('UTILITIES', 'Utilities'),
        ('CONSUMABLES', 'Consumables'),
        # Storage
        ('PACKAGING', 'Packaging Materials'),
        ('STORAGE_EQUIPMENT', 'Storage Equipment'),
        # Transport
        ('TRANSPORT_EQUIPMENT', 'Transport Equipment'),
        ('TRANSPORT_CONSUMABLES', 'Transport Consumables'),
        # Labor
        ('LABOR_EQUIPMENT', 'Labor Equipment'),
        # Sales
        ('BUSINESS_MATERIALS', 'Business Materials'),
        # Emergency
        ('EMERGENCY_STOCK', 'Emergency Stock'),
        # Water
        ('WATER_EQUIPMENT', 'Water Equipment'),
        ('WATER_TREATMENT', 'Water Treatment'),
        # Hatchery
        ('HATCHERY_EQUIPMENT', 'Hatchery Equipment'),
        ('HATCHERY_SENSORS', 'Hatchery Sensors'),
        # Waste
        ('WASTE_PRODUCTS', 'Waste Products'),
        # Machinery
        ('FARM_MACHINERY', 'Farm Machinery'),
        ('FARM_TOOLS', 'Farm Tools'),
        # Office
        ('DIGITAL_EQUIPMENT', 'Digital Equipment'),
        ('OFFICE_SUPPLIES', 'Office Supplies'),
        # Financial
        ('FINANCIAL_RECORDS', 'Financial Records'),
        # Veterinary Tools
        ('VETERINARY_TOOLS', 'Veterinary Tools'),
        # Feed Supplements
        ('FEED_SUPPLEMENTS', 'Feed Supplements'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='inventory_items')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, null=True, blank=True, related_name='inventory_items', help_text="Farm this inventory belongs to")
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    subcategory = models.CharField(max_length=50, choices=SUBCATEGORY_CHOICES, null=True, blank=True, help_text="Subcategory for better organization")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=50)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=10)
    supplier = models.CharField(max_length=255, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    
    # Professional inventory management features
    # Feed-specific tracking (based on research for 1-18 days and 19-40 days old chickens)
    feed_stage = models.CharField(max_length=20, choices=[
        ('STARTER', 'Starter Feed (1-18 days)'),
        ('GROWER', 'Grower Feed (19-40 days)'),
        ('FINISHER', 'Finisher Feed (40+ days)'),
        ('LAYER', 'Layer Feed'),
        ('BREEDER', 'Breeder Feed'),
    ], null=True, blank=True, help_text="Feed stage based on bird age")
    
    # Quality control and shelf life management
    manufacture_date = models.DateField(null=True, blank=True, help_text="Manufacture/production date")
    shelf_life_days = models.IntegerField(null=True, blank=True, help_text="Shelf life in days")
    quality_grade = models.CharField(max_length=10, choices=[
        ('PREMIUM', 'Premium'),
        ('STANDARD', 'Standard'),
        ('ECONOMY', 'Economy'),
    ], default='STANDARD', help_text="Quality grade of the item")
    
    # Storage and environmental conditions
    storage_temperature_min = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Minimum storage temperature (°C)")
    storage_temperature_max = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Maximum storage temperature (°C)")
    humidity_requirement = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Required humidity (%)")
    ventilation_required = models.BooleanField(default=False, help_text="Requires special ventilation")
    
    # Financial and cost management
    supplier_price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Supplier price per unit")
    market_price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Current market price per unit")
    last_price_update = models.DateField(null=True, blank=True, help_text="Last price update date")
    
    # Inventory optimization parameters (s,S policy implementation)
    reorder_point = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Reorder point (s) - when to reorder")
    order_up_to_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Order-up-to level (S) - target inventory")
    safety_stock = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Safety stock level")
    lead_time_days = models.IntegerField(default=2, help_text="Lead time in days for replenishment")
    service_level_target = models.DecimalField(max_digits=5, decimal_places=2, default=95.0, help_text="Target service level (%)")
    
    # Tracking features
    feed_type = models.CharField(max_length=100, null=True, blank=True, help_text="Type of feed (for FEED category)")
    consumption_rate_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Daily consumption rate")
    course_days = models.IntegerField(null=True, blank=True, help_text="Course duration in days (for medicines)")
    requires_refrigeration = models.BooleanField(default=False, help_text="Requires cold storage")
    is_iot_device = models.BooleanField(default=False, help_text="IoT/Smart device")
    is_emergency_stock = models.BooleanField(default=False, help_text="Emergency stock item")
    
    # Batch tracking for all inventory categories
    batch = models.ForeignKey('Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_items', help_text="Associated batch for this inventory item")
    
    # Live bird specific tracking (if category is LIVE_BIRDS)
    age_days = models.IntegerField(null=True, blank=True, help_text="Age in days (for live birds)")
    average_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Average weight in kg")
    
    # Additional metadata
    barcode = models.CharField(max_length=100, null=True, blank=True, unique=True, help_text="Barcode/QR code for scanning")
    batch_number = models.CharField(max_length=100, null=True, blank=True, help_text="Batch/lot number")
    location = models.CharField(max_length=255, null=True, blank=True, help_text="Storage location")
    notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"
    
    def get_days_to_expiry(self):
        """Calculate days until expiry"""
        if not self.expiry_date:
            return None
        from datetime import date
        return (self.expiry_date - date.today()).days
    
    def is_near_expiry(self, days_threshold=30):
        """Check if item is near expiry"""
        days_to_expiry = self.get_days_to_expiry()
        return days_to_expiry is not None and days_to_expiry <= days_threshold
    
    def is_expired(self):
        """Check if item is expired"""
        days_to_expiry = self.get_days_to_expiry()
        return days_to_expiry is not None and days_to_expiry < 0
    
    def get_shelf_life_remaining_percentage(self):
        """Calculate percentage of shelf life remaining"""
        if not self.manufacture_date or not self.shelf_life_days:
            return None
        from datetime import date
        total_days = self.shelf_life_days
        days_passed = (date.today() - self.manufacture_date).days
        remaining_percentage = max(0, (total_days - days_passed) / total_days * 100)
        return remaining_percentage
    
    def should_reorder(self):
        """Check if item should be reordered based on (s,S) policy"""
        if not self.reorder_point:
            # Fallback to simple reorder level if reorder point not set
            return self.quantity <= self.reorder_level
        return self.quantity <= self.reorder_point
    
    def calculate_order_quantity(self):
        """Calculate optimal order quantity based on (s,S) policy"""
        if not self.order_up_to_level:
            return None
        return self.order_up_to_level - self.quantity
    
    def get_inventory_status(self):
        """Get comprehensive inventory status"""
        if self.is_expired():
            return 'EXPIRED'
        elif self.is_near_expiry():
            return 'NEAR_EXPIRY'
        elif self.should_reorder():
            return 'REORDER_REQUIRED'
        elif self.quantity <= self.reorder_level:
            return 'LOW_STOCK'
        else:
            return 'ADEQUATE'
    
    def calculate_total_cost(self):
        """Calculate total cost of current inventory"""
        return float(self.quantity) * float(self.cost_per_unit)
    
    def calculate_market_value(self):
        """Calculate current market value"""
        if not self.market_price_per_unit:
            return self.calculate_total_cost()
        return float(self.quantity) * float(self.market_price_per_unit)
    
    def get_quality_impact_factor(self):
        """Get quality impact factor for pricing/valuation"""
        quality_factors = {
            'PREMIUM': 1.1,
            'STANDARD': 1.0,
            'ECONOMY': 0.9
        }
        return quality_factors.get(self.quality_grade, 1.0)

class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('PURCHASE', 'Stock In (Purchase)'),
        ('USAGE', 'Stock Out (Usage)'),
        ('ADJUSTMENT', 'Adjustment'),
        ('RETURN', 'Return'),
        ('WASTE', 'Wastage'),  # NEW: Explicit wastage tracking
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='transactions')
    batch = models.ForeignKey('Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_transactions', help_text="Associated batch/flock for this transaction")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    transaction_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    @transaction.atomic
    def save(self, *args, **kwargs):
        # Update specific item quantity on save
        if not self.pk:  # Only on create
            if self.transaction_type in ['PURCHASE', 'RETURN']:
                InventoryItem.objects.filter(id=self.item.id).update(
                    quantity=F('quantity') + self.quantity_change
                )
            elif self.transaction_type in ['USAGE', 'WASTE']:
                # Both USAGE and WASTE reduce inventory
                InventoryItem.objects.filter(id=self.item.id).update(
                    quantity=F('quantity') - abs(self.quantity_change)
                )
            elif self.transaction_type == 'ADJUSTMENT':
                # For adjustment, quantity_change can be positive or negative
                InventoryItem.objects.filter(id=self.item.id).update(
                    quantity=F('quantity') + self.quantity_change
                )
            # Refresh from DB to ensure local object has correct value if needed after super().save()
            self.item.refresh_from_db()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type} - {self.item.name} ({self.quantity_change})"


class FeedConsumption(models.Model):
    """
    Tracks feed consumption per batch/flock for accurate feed reporting
    Links inventory usage to specific flocks
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey('Batch', on_delete=models.CASCADE, related_name='feed_consumption')
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='feed_consumption_records')
    quantity_used = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantity consumed in item's unit")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Cost per unit at time of consumption")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total cost (auto-calculated)")
    date = models.DateField(default=timezone.now, help_text="Date of consumption")
    notes = models.TextField(null=True, blank=True, help_text="Additional notes about consumption")
    transaction = models.ForeignKey(InventoryTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='feed_consumption', help_text="Link to inventory transaction")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['batch', 'date']),
            models.Index(fields=['inventory_item', 'date']),
        ]

    def save(self, *args, **kwargs):
        # Auto-calculate total cost
        if self.unit_cost and self.quantity_used:
            self.total_cost = self.unit_cost * self.quantity_used
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.batch.batch_number} - {self.inventory_item.name} ({self.quantity_used} {self.inventory_item.unit}) on {self.date}"


class InventoryAlert(models.Model):
    """
    Tracks inventory alerts for low stock, expiry warnings, etc.
    """
    ALERT_TYPES = [
        ('LOW_STOCK', 'Low Stock'),
        ('EXPIRY_WARNING', 'Expiry Warning'),
        ('EXPIRED', 'Expired'),
        ('OUT_OF_STOCK', 'Out of Stock'),
        ('HIGH_CONSUMPTION', 'High Consumption Rate'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.CharField(max_length=255, help_text="Human-readable alert message")
    severity = models.CharField(max_length=10, choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')], default='MEDIUM')
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['item', 'is_resolved']),
            models.Index(fields=['alert_type', 'is_resolved']),
        ]

    def resolve(self, user=None):
        """Mark alert as resolved"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        if user:
            self.resolved_by = user
        self.save()

    def __str__(self):
        return f"{self.alert_type} - {self.item.name} - {self.message}"

class HealthRecord(models.Model):
    RECORD_TYPES = [
        ('VACCINATION', 'Vaccination'),
        ('MEDICATION', 'Medication'),
        ('DISEASE', 'Disease Report'),
        ('INJURY', 'Injury'),
        ('CHECKUP', 'Routine Checkup'),
        ('LAB_RESULT', 'Lab Result'),
    ]

    OUTCOME_CHOICES = [
        ('RECOVERED', 'Recovered'),
        ('UNDER_TREATMENT', 'Under Treatment'),
        ('DIED', 'Died'),
        ('CULLED', 'Culled'),
        ('UNKNOWN', 'Unknown'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='health_records')
    affected_batch = models.ForeignKey('Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='health_records', help_text="Batch closely monitored")
    reported_by = models.ForeignKey(FarmerProfile, on_delete=models.SET_NULL, null=True, blank=True)
    
    record_type = models.CharField(max_length=20, choices=RECORD_TYPES)
    date = models.DateField(default=timezone.now)
    
    # Clinical details
    symptoms = models.TextField(null=True, blank=True, help_text="Observed symptoms")
    diagnosis = models.CharField(max_length=255, null=True, blank=True)
    treatment_plan = models.TextField(null=True, blank=True, help_text="Medication or action taken")
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default='UNDER_TREATMENT', blank=True)
    
    notes = models.TextField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True, help_text="Cost of treatment")
    next_followup_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Health Record'
        verbose_name_plural = 'Health Records'

    def __str__(self):
        return f"{self.record_type} - {self.date}"
# Enhanced Inventory Models for FugajiSmart
# Append these models to the end of apps/consolidated/models.py

# ==================== MEDICINE & VACCINE INVENTORY ====================

class MedicineInventory(models.Model):
    """Dedicated model for medicine and vaccine tracking"""
    
    MEDICINE_TYPES = [
        ('ANTIBIOTIC', 'Antibiotics'),
        ('VITAMIN', 'Vitamins'),
        ('DEWORMER', 'Dewormers'),
        ('ANTI_STRESS', 'Anti-stress Solutions'),
        ('ELECTROLYTE', 'Electrolytes'),
        ('DISINFECTANT', 'Disinfectants'),
    ]
    
    VACCINE_TYPES = [
        ('NEWCASTLE', 'Newcastle Disease'),
        ('GUMBORO', 'Gumboro (IBD)'),
        ('FOWL_POX', 'Fowl Pox'),
        ('MAREKS', 'Marek\'s Disease'),
        ('IB_VACCINE', 'Infectious Bronchitis'),
        ('FOWL_TYPHOID', 'Fowl Typhoid'),
        ('LASOTA', 'Lasota (Newcastle Booster)'),
        ('HITCHNER_B1', 'Hitchner B1'),
    ]
    
    ADMINISTRATION_ROUTES = [
        ('ORAL', 'Oral/Drinking Water'),
        ('INJECTION_IM', 'Intramuscular Injection'),
        ('INJECTION_SC', 'Subcutaneous Injection'),
        ('EYE_DROP', 'Eye Drop'),
        ('WING_STAB', 'Wing Stab'),
        ('SPRAY', 'Spray'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item = models.OneToOneField('InventoryItem', on_delete=models.CASCADE, related_name='medicine_details')
    medicine_type = models.CharField(max_length=20, choices=MEDICINE_TYPES, null=True, blank=True)
    vaccine_type = models.CharField(max_length=20, choices=VACCINE_TYPES, null=True, blank=True)
    purpose = models.TextField(help_text="Purpose/indication for use")
    dosage = models.CharField(max_length=255, help_text="Recommended dosage (e.g., 1ml per liter)")
    administration_route = models.CharField(max_length=20, choices=ADMINISTRATION_ROUTES, default='ORAL')
    withdrawal_period_days = models.IntegerField(null=True, blank=True, help_text="Days before slaughter/egg consumption")
    storage_temperature = models.CharField(max_length=50, null=True, blank=True, help_text="e.g., 2-8°C, Room Temperature")
    manufacturer = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Medicine/Vaccine Inventory'
        verbose_name_plural = 'Medicine/Vaccine Inventories'
    
    def __str__(self):
        return f"{self.inventory_item.name} - {self.get_medicine_type_display() or self.get_vaccine_type_display()}"


class MedicineAdministration(models.Model):
    """Track medicine/vaccine administration to flocks"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medicine = models.ForeignKey(MedicineInventory, on_delete=models.CASCADE, related_name='administrations')
    batch = models.ForeignKey('Batch', on_delete=models.CASCADE, related_name='medicine_records')
    administered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='medicine_administrations')
    administered_date = models.DateTimeField(default=timezone.now)
    dosage_given = models.CharField(max_length=255, help_text="Actual dosage administered")
    number_of_birds = models.IntegerField(help_text="Number of birds treated")
    reason = models.TextField(help_text="Reason for administration (disease, prevention, etc.)")
    notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-administered_date']
        verbose_name = 'Medicine Administration Record'
        verbose_name_plural = 'Medicine Administration Records'
    
    def __str__(self):
        return f"{self.medicine.inventory_item.name} - {self.batch.batch_name} ({self.administered_date.date()})"


# ==================== EQUIPMENT & TOOLS INVENTORY ====================

class EquipmentInventory(models.Model):
    """Track farm equipment and tools"""
    
    EQUIPMENT_TYPES = [
        ('FEEDER', 'Feeders'),
        ('DRINKER', 'Drinkers'),
        ('BROODER', 'Brooders'),
        ('INCUBATOR', 'Incubators'),
        ('EGG_TRAY', 'Egg Trays'),
        ('CRATE', 'Crates'),
        ('WEIGHING_SCALE', 'Weighing Scales'),
        ('WATER_TANK', 'Water Tanks'),
        ('HEATER', 'Heaters'),
        ('FAN', 'Fans/Ventilation'),
        ('GENERATOR', 'Generator'),
        ('SPRAYER', 'Sprayers'),
        ('THERMOMETER', 'Thermometers'),
        ('HYGROMETER', 'Hygrometers'),
    ]
    
    CONDITION_CHOICES = [
        ('EXCELLENT', 'Excellent'),
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('DAMAGED', 'Damaged'),
        ('NEEDS_REPAIR', 'Needs Repair'),
        ('RETIRED', 'Retired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item = models.OneToOneField('InventoryItem', on_delete=models.CASCADE, related_name='equipment_details')
    equipment_type = models.CharField(max_length=20, choices=EQUIPMENT_TYPES)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='GOOD')
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2)
    expected_lifespan_years = models.DecimalField(max_digits=5, decimal_places=1, help_text="Expected lifespan in years")
    installation_date = models.DateField(null=True, blank=True)
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    replacement_alert = models.BooleanField(default=False, help_text="Alert when nearing end of lifespan")
    warranty_expiry = models.DateField(null=True, blank=True)
    serial_number = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Equipment Inventory'
        verbose_name_plural = 'Equipment Inventories'
    
    def __str__(self):
        return f"{self.inventory_item.name} - {self.get_condition_display()}"


# ==================== LABOR & SERVICES ====================

class LaborRecord(models.Model):
    """Track farm workers and labor costs"""
    
    WORKER_TYPES = [
        ('PERMANENT', 'Permanent Staff'),
        ('CASUAL', 'Casual Labor'),
        ('CONTRACT', 'Contract Worker'),
    ]
    
    PAYMENT_FREQUENCY = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='labor_records')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, null=True, blank=True, related_name='workers')
    worker_name = models.CharField(max_length=255)
    worker_type = models.CharField(max_length=20, choices=WORKER_TYPES)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    role = models.CharField(max_length=100, help_text="e.g., Farm Manager, Cleaner, Feeder")
    payment_frequency = models.CharField(max_length=20, choices=PAYMENT_FREQUENCY)
    wage_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Wage amount per payment period")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Labor Record'
        verbose_name_plural = 'Labor Records'
    
    def __str__(self):
        return f"{self.worker_name} - {self.role} ({self.get_worker_type_display()})"


class ServiceExpense(models.Model):
    """Track service expenses (vet, transport, etc.)"""
    
    SERVICE_TYPES = [
        ('VETERINARY', 'Veterinary Services'),
        ('TRANSPORT', 'Transport/Logistics'),
        ('CONSULTATION', 'Consultation Fees'),
        ('MAINTENANCE', 'Equipment Maintenance'),
        ('CLEANING', 'Cleaning Services'),
        ('LABORATORY', 'Laboratory/Testing Services'),
        ('OTHER', 'Other Services'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='service_expenses')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, null=True, blank=True, related_name='service_expenses')
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    service_provider = models.CharField(max_length=255)
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    service_date = models.DateField()
    invoice_number = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-service_date']
        verbose_name = 'Service Expense'
        verbose_name_plural = 'Service Expenses'
    
    def __str__(self):
        return f"{self.get_service_type_display()} - {self.service_provider} ({self.service_date})"


# ==================== HEALTH ALERTS ====================

class HealthAlert(models.Model):
    """Automated health alerts based on flock performance"""
    
    ALERT_TYPES = [
        ('ABNORMAL_MORTALITY', 'Abnormal Mortality Rate'),
        ('EGG_DROP', 'Drop in Egg Production'),
        ('FEED_INTAKE_LOW', 'Low Feed Intake'),
        ('WATER_INTAKE_HIGH', 'Excessive Water Consumption'),
        ('WEIGHT_LOSS', 'Weight Loss Detected'),
        ('DISEASE_OUTBREAK', 'Potential Disease Outbreak'),
    ]
    
    SEVERITY_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey('Batch', on_delete=models.CASCADE, related_name='health_alerts')
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    message = models.TextField()
    detected_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Actual value that triggered alert")
    threshold_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Threshold that was exceeded")
    detected_at = models.DateTimeField(default=timezone.now)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_health_alerts')
    resolution_notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-detected_at']
        verbose_name = 'Health Alert'
        verbose_name_plural = 'Health Alerts'
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.batch.batch_name} ({self.get_severity_display()})"


# ==================== EGG INVENTORY & SALES ====================

class EggInventory(models.Model):
    """Detailed egg inventory and grading"""
    
    EGG_GRADES = [
        ('SMALL', 'Small (< 50g)'),
        ('MEDIUM', 'Medium (50-60g)'),
        ('LARGE', 'Large (60-70g)'),
        ('EXTRA_LARGE', 'Extra Large (> 70g)'),
    ]
    
    EGG_QUALITY = [
        ('GRADE_A', 'Grade A (Premium)'),
        ('GRADE_B', 'Grade B (Standard)'),
        ('GRADE_C', 'Grade C (Below Standard)'),
        ('SPOILED', 'Spoiled/Cracked'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey('Batch', on_delete=models.CASCADE, related_name='egg_inventory')
    collection_date = models.DateField()
    grade = models.CharField(max_length=15, choices=EGG_GRADES)
    quality = models.CharField(max_length=10, choices=EGG_QUALITY)
    quantity_trays = models.DecimalField(max_digits=10, decimal_places=2, help_text="Number of trays (30 eggs/tray)")
    quantity_pieces = models.IntegerField(help_text="Individual eggs")
    spoiled_count = models.IntegerField(default=0)
    available_stock = models.IntegerField(help_text="Current available stock in pieces")
    price_per_tray = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_piece = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-collection_date']
        verbose_name = 'Egg Inventory'
        verbose_name_plural = 'Egg Inventories'
    
    def __str__(self):
        return f"{self.batch.batch_name} - {self.get_grade_display()} {self.get_quality_display()} ({self.collection_date})"
    
    def save(self, *args, **kwargs):
        # Auto-calculate price per piece if not provided
        if not self.price_per_piece and self.price_per_tray:
            self.price_per_piece = self.price_per_tray / 30
        super().save(*args, **kwargs)


class EggSale(models.Model):
    """Track egg sales and customers"""
    
    CUSTOMER_TYPES = [
        ('RETAIL', 'Retail Customer'),
        ('WHOLESALE', 'Wholesale'),
        ('RESTAURANT', 'Restaurant/Hotel'),
        ('SUPERMARKET', 'Supermarket'),
        ('DISTRIBUTOR', 'Distributor'),
    ]
    
    PAYMENT_STATUS = [
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partial Payment'),
        ('OVERDUE', 'Overdue'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    egg_inventory = models.ForeignKey(EggInventory, on_delete=models.CASCADE, related_name='sales')
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES)
    quantity_sold = models.IntegerField(help_text="Quantity in pieces")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per piece or tray")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    sale_date = models.DateField()
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    payment_date = models.DateField(null=True, blank=True)
    invoice_number = models.CharField(max_length=100, null=True, blank=True, unique=True)
    notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-sale_date']
        verbose_name = 'Egg Sale'
        verbose_name_plural = 'Egg Sales'
    
    def __str__(self):
        return f"{self.customer_name} - {self.quantity_sold} eggs ({self.sale_date})"
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        # Update egg inventory stock when sale is created
        if not self.pk:  # Only on create
            EggInventory.objects.filter(id=self.egg_inventory.id).update(
                available_stock=F('available_stock') - self.quantity_sold
            )
        super().save(*args, **kwargs)
