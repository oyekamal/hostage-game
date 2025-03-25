from django.db import migrations
from datetime import datetime

def populate_scenarios(apps, schema_editor):
    Scenario = apps.get_model('game', 'Scenario')
    
    # Clear existing scenarios to avoid duplicates
    Scenario.objects.all().delete()
    
    # Import scenarios data
    from ..scenario_manager import ScenarioManager
    
    # Populate database with scenarios
    for scenario in ScenarioManager._scenarios:
        Scenario.objects.create(
            name=scenario.name,
            setting=scenario.setting,
            suspect=scenario.suspect,
            initial_mood=scenario.initial_mood,
            hostages=scenario.hostages,
            opening_dialogue=scenario.opening_dialogue,
            demand=scenario.demand,
            goal=scenario.goal,
            suspect_type=scenario.suspect_type,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

def reverse_populate_scenarios(apps, schema_editor):
    Scenario = apps.get_model('game', 'Scenario')
    Scenario.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('game', '0004_alter_scenario_options_and_more'),  # Make sure this matches your previous migration
    ]

    operations = [
        migrations.RunPython(populate_scenarios, reverse_populate_scenarios),
    ]