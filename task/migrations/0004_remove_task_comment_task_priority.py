# Generated by Django 5.1.4 on 2025-01-17 12:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('task', '0003_rename_parent_project_task_to_project_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='task',
            name='comment',
        ),
        migrations.AddField(
            model_name='task',
            name='priority',
            field=models.IntegerField(blank=True, default=1),
            preserve_default=False,
        ),
    ]
