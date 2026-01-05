from django.db import migrations, models
import django.db.models.deletion
import uuid
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('consolidated', '0005_alter_breedconfiguration_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='HealthRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('record_type', models.CharField(choices=[('VACCINATION', 'Vaccination'), ('MEDICATION', 'Medication'), ('DISEASE', 'Disease Report'), ('INJURY', 'Injury'), ('CHECKUP', 'Routine Checkup'), ('LAB_RESULT', 'Lab Result')], max_length=20)),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('symptoms', models.TextField(blank=True, help_text='Observed symptoms', null=True)),
                ('diagnosis', models.CharField(blank=True, max_length=255, null=True)),
                ('treatment_plan', models.TextField(blank=True, help_text='Medication or action taken', null=True)),
                ('outcome', models.CharField(blank=True, choices=[('RECOVERED', 'Recovered'), ('UNDER_TREATMENT', 'Under Treatment'), ('DIED', 'Died'), ('CULLED', 'Culled'), ('UNKNOWN', 'Unknown')], default='UNDER_TREATMENT', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('cost', models.DecimalField(blank=True, decimal_places=2, default=0, help_text='Cost of treatment', max_digits=10, null=True)),
                ('next_followup_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('affected_batch', models.ForeignKey(blank=True, help_text='Batch closely monitored', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='health_records', to='consolidated.batch')),
                ('farm', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='health_records', to='consolidated.farm')),
                ('reported_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='consolidated.farmerprofile')),
            ],
            options={
                'ordering': ['-date', '-created_at'],
                'verbose_name': 'Health Record',
                'verbose_name_plural': 'Health Records',
            },
        ),
    ]
