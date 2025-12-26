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
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='FARMER')
    phone = models.CharField(max_length=20, blank=True, null=True)
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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile', primary_key=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    experience_years = models.PositiveIntegerField(default=0)
    verification_status = models.CharField(max_length=10, default='PENDING')
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
        # Feed
        ('COMPLETE_FEEDS', 'Complete Feeds'),
        ('FEED_INGREDIENTS', 'Feed Ingredients (Raw Materials)'),
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
    
    # Tracking features
    feed_type = models.CharField(max_length=100, null=True, blank=True, help_text="Type of feed (for FEED category)")
    consumption_rate_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Daily consumption rate")
    course_days = models.IntegerField(null=True, blank=True, help_text="Course duration in days (for medicines)")
    requires_refrigeration = models.BooleanField(default=False, help_text="Requires cold storage")
    is_iot_device = models.BooleanField(default=False, help_text="IoT/Smart device")
    is_emergency_stock = models.BooleanField(default=False, help_text="Emergency stock item")
    
    # Live bird tracking (if category is LIVE_BIRDS)
    batch = models.ForeignKey('Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_birds', help_text="Associated batch for live birds")
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
