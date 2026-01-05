
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_admin():
    email = "admin@amazingkuku.com"
    password = "password123"
    
    if User.objects.filter(email=email).exists():
        print(f"Superuser {email} already exists")
    else:
        # Depending on the custom user model, 'username' might not be a field, 
        # but create_superuser usually expects the USERNAME_FIELD.
        # We'll assume email is the unique identifier.
        try:
            user = User.objects.create_superuser(
                email=email, 
                password=password,
                role='ADMIN',
                first_name='Super',
                last_name='Admin'
            )
            print(f"Created superuser: {email} / {password}")
        except Exception as e:
            print(f"Error creating superuser: {e}")

if __name__ == "__main__":
    create_admin()
