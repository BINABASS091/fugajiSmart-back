from django.core.management.base import BaseCommand
from apps.consolidated.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Creates initial subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'Free',
                'description': 'Basic features for small-scale farmers',
                'price': 0,
                'duration_days': 30,
                'max_farms': 1,
                'max_devices': 1,
                'features': {
                    'max_birds': 10,
                    'max_batches': 1,
                    'disease_predictions': 5,
                    'has_analytics': False,
                    'has_support': False
                },
                'is_active': True
            },
            {
                'name': 'Basic',
                'description': 'For small to medium farms',
                'price': 29.99,
                'duration_days': 30,
                'max_farms': 3,
                'max_devices': 3,
                'features': {
                    'max_birds': 100,
                    'max_batches': 5,
                    'disease_predictions': 50,
                    'has_analytics': True,
                    'has_support': False
                },
                'is_active': True
            },
            {
                'name': 'Premium',
                'description': 'For larger farms with advanced features',
                'price': 99.99,
                'duration_days': 30,
                'max_farms': 10,
                'max_devices': 10,
                'features': {
                    'max_birds': 1000,
                    'max_batches': 20,
                    'disease_predictions': 500,
                    'has_analytics': True,
                    'has_support': True
                },
                'is_active': True
            },
            {
                'name': 'Enterprise',
                'description': 'For large-scale operations',
                'price': 299.99,
                'duration_days': 30,
                'max_farms': 50,
                'max_devices': 50,
                'features': {
                    'max_birds': 10000,
                    'max_batches': 100,
                    'disease_predictions': 2000,
                    'has_analytics': True,
                    'has_support': True
                },
                'is_active': True
            }
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{status} {plan.name} plan'))
