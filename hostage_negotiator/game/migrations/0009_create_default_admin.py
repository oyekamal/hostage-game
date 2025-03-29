from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_default_admin(apps, schema_editor):
    User = apps.get_model('game', 'User')
    
    # Check if admin user already exists
    if not User.objects.filter(username='admin').exists():
        User.objects.create(
            username='admin',
            email='admin@gmail.com',
            password=make_password('admin'),
            is_staff=True,
            is_superuser=True,
            is_active=True
        )

def reverse_default_admin(apps, schema_editor):
    User = apps.get_model('game', 'User')
    User.objects.filter(username='admin', email='admin@gmail.com').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('game', '0008_scenarioattempt_emotional_labeling_failure_and_more'),
    ]

    operations = [
        migrations.RunPython(create_default_admin, reverse_default_admin),
    ]