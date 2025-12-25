
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_user():
    email = "test@example.com"
    password = "password123"
    
    if User.objects.filter(email=email).exists():
        print(f"User {email} already exists")
    else:
        user = User.objects.create_user(
            email=email, 
            password=password, 
            role="ADMIN",
            first_name="Test",
            last_name="Admin"
        )
        print(f"Created user: {email} / {password}")

if __name__ == "__main__":
    create_user()
