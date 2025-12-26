from django.core.management.base import BaseCommand
from apps.consolidated.models import BreedConfiguration, BreedStage, BreedMilestone, Recommendation, User
from django.db import transaction

class Command(BaseCommand):
    help = 'Seeds the database with poultry breeds and recommendations'

    def handle(self, *args, **options):
        self.stdout.write('Seeding knowledge base data...')

        with transaction.atomic():
            # Get an admin user for the 'created_by' field
            admin_user = User.objects.filter(role='ADMIN').first()
            if not admin_user:
                self.stdout.write(self.style.WARNING('No admin user found. Creating recommendations without owner.'))

            # 1. BREED CONFIGURATIONS
            
            # --- COBB 500 (Broiler) ---
            cobb, created = BreedConfiguration.objects.get_or_create(
                breed_name='Cobb 500',
                defaults={
                    'breed_type': 'BROILER',
                    'description': 'The world\'s most effective broiler. Known for high growth rate and excellent feed conversion.',
                    'average_maturity_days': 42,
                    'production_lifespan_days': 45,
                    'average_weight_kg': 2.8,
                    'feed_conversion_ratio': 1.6,
                    'feed_consumption_daily_grams': 120.0,
                    'space_requirement_sqm': 0.1,
                    'temperature_min_celsius': 20.0,
                    'temperature_max_celsius': 32.0,
                    'growth_speed': 'Very Fast',
                    'hardiness': 'Moderate'
                }
            )

            if created:
                # Stages for Cobb 500
                starter = BreedStage.objects.create(
                    breed=cobb,
                    stage_name='Starter Phase',
                    start_day=0,
                    end_day=10,
                    description='Rapid early development and immune system priming.',
                    feeding_guide='Feed Broiler Starter crumbs ad libitum.',
                    health_tips='Maintain steady temperature to prevent brooding stress.',
                    feed_type='Broiler Starter (22% Protein)',
                    expected_weight_kg=0.3
                )

                finisher = BreedStage.objects.create(
                    breed=cobb,
                    stage_name='Finisher Phase',
                    start_day=11,
                    end_day=42,
                    description='Maximum muscle mass deposition and weight gain.',
                    feeding_guide='Feed Broiler Finisher pellets.',
                    feed_type='Broiler Finisher (18% Protein)',
                    expected_weight_kg=2.5
                )

                # Milestones
                BreedMilestone.objects.create(
                    breed=cobb,
                    milestone_day=1,
                    milestone_title='Arrival & Gumboro 1',
                    milestone_description='Critical arrival check and first Gumboro vaccination.',
                    action_required='Administer vaccine via drinking water.',
                    is_critical=True
                )
                
                BreedMilestone.objects.create(
                    breed=cobb,
                    milestone_day=21,
                    milestone_title='Newcastle Booster',
                    milestone_description='Newcastle disease prevention booster.',
                    action_required='Eye drop or spray administration.',
                    is_critical=True
                )

            # --- ISA Brown (Layer) ---
            isa, created = BreedConfiguration.objects.get_or_create(
                breed_name='ISA Brown',
                defaults={
                    'breed_type': 'LAYER',
                    'description': 'The global leader in high-quality brown egg production.',
                    'average_maturity_days': 126, # 18 weeks
                    'production_lifespan_days': 560, # 80 weeks
                    'average_weight_kg': 2.0,
                    'eggs_per_year': 320,
                    'feed_consumption_daily_grams': 110.0,
                    'space_requirement_sqm': 0.15,
                    'temperature_min_celsius': 18.0,
                    'temperature_max_celsius': 25.0,
                    'growth_speed': 'Moderate',
                    'hardiness': 'High'
                }
            )

            if created:
                BreedStage.objects.create(
                    breed=isa,
                    stage_name='Laying Phase',
                    start_day=140,
                    end_day=560,
                    description='Peak egg production period.',
                    feeding_guide='Feed Layers Mash with high calcium content.',
                    feed_type='Layers Mash (16% Protein, 4% Calcium)',
                    expected_weight_kg=2.0
                )

            # 2. RECOMMENDATIONS (Insights)
            
            recs = [
                {
                    'title': 'Biosecurity Air-Lock Protocol',
                    'category': 'BIOSECURITY',
                    'content': 'Always implement a "footbath" at the entrance of every coop. Use a solution of iodine-based disinfectant. This reduces the risk of introducing Newcastle or Gumboro pathogens by 85%.'
                },
                {
                    'title': 'Optimizing Early Morning Feeding',
                    'category': 'FEEDING',
                    'content': 'Poultry consume 60% of their daily requirement in the first 4 hours of daylight. Ensure feeders are cleaned and refilled BEFORE sunrise for maximum FCR efficiency.'
                },
                {
                    'title': 'Heat Stress Mitigation',
                    'category': 'ENVIRONMENT',
                    'content': 'When temperatures exceed 32°C, add electrolytes to drinking water and reduce feed density. Increase ventilation and avoid handling birds during peak heat hours.'
                },
                {
                    'title': 'Respiratory Health Indicator',
                    'category': 'HEALTH',
                    'content': 'Listen for "sneezing" or "snicking" during the quiet of the night. This is the earliest warning sign of Infectious Bronchitis or Mycoplasma.'
                }
            ]

            for rec_data in recs:
                Recommendation.objects.get_or_create(
                    title=rec_data['title'],
                    defaults={
                        'category': rec_data['category'],
                        'content': rec_data['content'],
                        'created_by': admin_user
                    }
                )

        self.stdout.write(self.style.SUCCESS('Successfully seeded knowledge base data.'))
