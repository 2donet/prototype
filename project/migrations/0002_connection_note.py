# Generated by Django 5.1.4 on 2025-07-26 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='connection',
            name='note',
            field=models.TextField(blank=True, help_text='Optional note about the connection', null=True),
        ),
    ]
