import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.consolidated.models import User, FarmerProfile

EMAIL = 'bitam10-091@suza.ac.tz'
PASSWORD = 'changeme123'  # Set a secure password here

user, created = User.objects.get_or_create(email=EMAIL, defaults={
    'role': 'FARMER',
    'is_active': True,
    'first_name': 'Abdul-Latif',
    'last_name': 'Suleiman',
})

if not created:
    user.is_active = True
    user.role = 'FARMER'
    user.first_name = 'Abdul-Latif'
    user.last_name = 'Suleiman'
    user.set_password(PASSWORD)
    user.save()
    print(f'Updated user: {EMAIL}')
else:
    user.set_password(PASSWORD)
    user.save()
    print(f'Created user: {EMAIL}')

# Ensure FarmerProfile exists
if not hasattr(user, 'farmer_profile'):
    FarmerProfile.objects.create(user=user)
    print('Created FarmerProfile for user.')
else:
    print('FarmerProfile already exists.')

print('Done.')
