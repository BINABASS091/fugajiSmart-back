import os
import django
import sys

def check_settings():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    try:
        django.setup()
        print("Django setup completed successfully!")
        
        # Check database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print(f"Database connection test: {'Success' if result and result[0] == 1 else 'Failed'}")
        
        # Check installed apps
        from django.conf import settings
        print("\nInstalled Apps:")
        for app in settings.INSTALLED_APPS:
            print(f"- {app}")
            
        # Check database settings
        print("\nDatabase Settings:")
        for key, value in settings.DATABASES['default'].items():
            if 'PASSWORD' in key.upper() and value:
                value = '********'  # Don't show password
            print(f"{key}: {value}")
            
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_settings()
