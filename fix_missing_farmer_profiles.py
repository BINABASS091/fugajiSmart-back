# Script to ensure every user with role FARMER has a FarmerProfile

from django.contrib.auth import get_user_model
from apps.consolidated.models import FarmerProfile

User = get_user_model()

def ensure_farmer_profiles():
    created = 0
    for user in User.objects.filter(role='FARMER'):
        if not hasattr(user, 'farmer_profile') or user.farmer_profile is None:
            FarmerProfile.objects.create(user=user)
            print(f"Created FarmerProfile for user: {user.email}")
            created += 1
    if created == 0:
        print("All FARMER users already have FarmerProfiles.")
    else:
        print(f"Created {created} FarmerProfiles.")

if __name__ == "__main__":
    ensure_farmer_profiles()
