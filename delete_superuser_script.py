
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def delete_admin():
    email = "admin@amazingkuku.com"
    
    try:
        user = User.objects.get(email=email)
        user.delete()
        print(f"Deleted superuser: {email}")
    except User.DoesNotExist:
        print(f"Superuser {email} does not exist")
    except Exception as e:
        print(f"Error deleting superuser: {e}")

if __name__ == "__main__":
    delete_admin()
