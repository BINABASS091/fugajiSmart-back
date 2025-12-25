import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    breed_name = models.CharField(max_length=255, unique=True)
    breed_type = models.CharField(max_length=20)
    description = models.TextField(null=True, blank=True)
    average_maturity_days = models.IntegerField(default=0)
    production_lifespan_days = models.IntegerField(default=0)
    average_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    eggs_per_year = models.IntegerField(default=0)
    feed_consumption_daily_grams = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    space_requirement_sqm = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    temperature_min_celsius = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    temperature_max_celsius = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    humidity_min_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    humidity_max_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.breed_name

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
    CATEGORY_CHOICES = [
        ('FEED', 'Feed'),
        ('MEDICINE', 'Medicine'),
        ('EQUIPMENT', 'Equipment'),
        ('OTHER', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='inventory_items')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, null=True, blank=True, related_name='inventory_items', help_text="Farm this inventory belongs to")
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=50)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=10)
    supplier = models.CharField(max_length=255, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
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
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    transaction_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Update specific item quantity on save
        if not self.pk:  # Only on create
            if self.transaction_type in ['PURCHASE', 'RETURN']:
                self.item.quantity += self.quantity_change
            elif self.transaction_type == 'USAGE':
                self.item.quantity -= self.quantity_change
            elif self.transaction_type == 'ADJUSTMENT':
                # For adjustment, quantity_change can be positive or negative
                self.item.quantity += self.quantity_change
            self.item.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type} - {self.item.name} ({self.quantity_change})"
