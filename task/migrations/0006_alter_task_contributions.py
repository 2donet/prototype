# Generated by Django 5.1.4 on 2025-02-02 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('task', '0005_task_contributions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='contributions',
            field=models.JSONField(null=True),
        ),
    ]
