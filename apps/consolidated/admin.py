from django.contrib import admin
from .models import (
    User, Batch, BreedConfiguration, Farm, Subscription, 
    SubscriptionPlan, FarmerProfile, BreedStage, BreedMilestone,
    Device, Recommendation, Payment, UserFeatureAccess, Alert, Activity
)

# Register your models here
admin.site.register(User)
admin.site.register(Batch)
admin.site.register(BreedConfiguration)
admin.site.register(Farm)
admin.site.register(Subscription)
admin.site.register(SubscriptionPlan)
admin.site.register(FarmerProfile)
admin.site.register(BreedStage)
admin.site.register(BreedMilestone)
admin.site.register(Device)
admin.site.register(Recommendation)
admin.site.register(Payment)
admin.site.register(UserFeatureAccess)
admin.site.register(Alert)
admin.site.register(Activity)
