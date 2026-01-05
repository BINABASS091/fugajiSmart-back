from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.consolidated.models import (
    BreedConfiguration, BreedStage, BreedMilestone,
    SubscriptionPlan, UserFeatureAccess
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed initial data for the application'

    def handle(self, *args, **options):
        self.stdout.write('Seeding initial data...')
        
        # Create Breed Configuration
        broiler, _ = BreedConfiguration.objects.get_or_create(
            name='Broiler',
            defaults={
                'description': 'Fast-growing chicken breed for meat production',
                'average_maturity_days': 42,
                'average_weight_kg': 2.5,
                'is_active': True
            }
        )
        
        # Create Breed Stages
        stages = [
            {
                'name': 'Starter',
                'start_day': 1,
                'end_day': 14,
                'description': 'Initial growth phase',
                'expected_weight_kg': 0.5
            },
            {
                'name': 'Grower',
                'start_day': 15,
                'end_day': 28,
                'description': 'Rapid growth phase',
                'expected_weight_kg': 1.5
            },
            {
                'name': 'Finisher',
                'start_day': 29,
                'end_day': 42,
                'description': 'Final growth phase before processing',
                'expected_weight_kg': 2.5
            }
        ]
        
        created_stages = []
        for stage_data in stages:
            stage, _ = BreedStage.objects.get_or_create(
                breed=broiler,
                name=stage_data['name'],
                defaults={
                    'start_day': stage_data['start_day'],
                    'end_day': stage_data['end_day'],
                    'description': stage_data['description'],
                    'expected_weight_kg': stage_data['expected_weight_kg']
                }
            )
            created_stages.append(stage)
        
        # Create Breed Milestones
        milestones = [
            {'stage': 'Starter', 'day': 7, 'title': 'First Week Check', 'description': 'Check for proper growth and health'},
            {'stage': 'Grower', 'day': 21, 'title': 'Mid-Growth Check', 'description': 'Monitor weight gain and adjust feed'},
            {'stage': 'Finisher', 'day': 35, 'title': 'Pre-Harvest Check', 'description': 'Final health and weight check'}
        ]
        
        for milestone_data in milestones:
            stage = next(s for s in created_stages if s.name == milestone_data['stage'])
            BreedMilestone.objects.get_or_create(
                breed=broiler,
                stage=stage,
                milestone_day=milestone_data['day'],
                defaults={
                    'milestone_title': milestone_data['title'],
                    'milestone_description': milestone_data['description'],
                    'is_critical': True
                }
            )
        
        # Create Subscription Plans
        plans = [
            {
                'name': 'Free',
                'description': 'Basic features for small-scale farmers',
                'price': 0,
                'duration_days': 30,
                'max_farms': 1,
                'max_devices': 2,
                'features': {
                    'can_add_farm': True,
                    'can_add_batch': True,
                    'can_add_inventory': True,
                    'can_view_analytics': False,
                    'can_export_data': False,
                    'can_use_api': False,
                    'max_batches_per_farm': 3,
                    'max_devices': 2
                }
            },
            {
                'name': 'Basic',
                'description': 'For small to medium farms',
                'price': 29.99,
                'duration_days': 30,
                'max_farms': 3,
                'max_devices': 10,
                'features': {
                    'can_add_farm': True,
                    'can_add_batch': True,
                    'can_add_inventory': True,
                    'can_view_analytics': True,
                    'can_export_data': True,
                    'can_use_api': False,
                    'max_batches_per_farm': 10,
                    'max_devices': 10
                }
            },
            {
                'name': 'Premium',
                'description': 'For professional poultry farmers',
                'price': 99.99,
                'duration_days': 30,
                'max_farms': 10,
                'max_devices': 50,
                'features': {
                    'can_add_farm': True,
                    'can_add_batch': True,
                    'can_add_inventory': True,
                    'can_view_analytics': True,
                    'can_export_data': True,
                    'can_use_api': True,
                    'max_batches_per_farm': 100,
                    'max_devices': 50
                }
            },
            {
                'name': 'Enterprise',
                'description': 'For large-scale commercial operations',
                'price': 299.99,
                'duration_days': 30,
                'max_farms': 100,
                'max_devices': 500,
                'features': {
                    'can_add_farm': True,
                    'can_add_batch': True,
                    'can_add_inventory': True,
                    'can_view_analytics': True,
                    'can_export_data': True,
                    'can_use_api': True,
                    'max_batches_per_farm': 1000,
                    'max_devices': 500,
                    'custom_features': True,
                    'dedicated_support': True,
                    'custom_integrations': True
                }
            }
        ]
        
        for plan_data in plans:
            SubscriptionPlan.objects.update_or_create(
                name=plan_data['name'],
                defaults={
                    'description': plan_data['description'],
                    'price': plan_data['price'],
                    'duration_days': plan_data['duration_days'],
                    'max_farms': plan_data['max_farms'],
                    'max_devices': plan_data['max_devices'],
                    'features': plan_data['features'],
                    'is_active': True
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded initial data!'))
