# Generated by Django 5.1.4 on 2024-12-25 16:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('task', '0002_task_parent_project_task_parent_task'),
    ]

    operations = [
        migrations.RenameField(
            model_name='task',
            old_name='parent_project',
            new_name='to_project',
        ),
        migrations.RenameField(
            model_name='task',
            old_name='parent_task',
            new_name='to_task',
        ),
    ]
