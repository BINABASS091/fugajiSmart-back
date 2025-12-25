from django.apps import AppConfig

# consolidated app package

# App configuration is now in apps.py

# Removed circular import
__all__ = []

default_app_config = 'apps.consolidated.apps.ConsolidatedConfig'