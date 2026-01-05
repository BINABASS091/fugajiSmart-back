"""
WSGI config for Vercel deployment.
"""
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    app = application
except Exception as e:
    print(f"Error loading Django application: {e}")
    import traceback
    traceback.print_exc()
    raise

