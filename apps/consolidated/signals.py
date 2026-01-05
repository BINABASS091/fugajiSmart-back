from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserFeatureAccess, SubscriptionPlan, Subscription, FarmerProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Create a FarmerProfile for new users
        FarmerProfile.objects.create(user=instance)
        
        # Create default feature access
        UserFeatureAccess.objects.create(user=instance)
        
        # Assign a default free subscription plan if available
        try:
            free_plan = SubscriptionPlan.objects.filter(
                is_active=True, 
                price=0
            ).first()
            
            if free_plan:
                Subscription.objects.create(
                    farmer=instance.farmer_profile,
                    plan=free_plan,
                    status='ACTIVE',
                    amount=0,
                    auto_renew=True
                )
        except Exception as e:
            # Log error but don't fail user creation
            print(f"Error creating subscription: {e}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'farmer_profile'):
        instance.farmer_profile.save()
