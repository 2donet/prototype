# Generated by Django 5.1.4 on 2025-02-09 18:00

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0009_remove_project_contributions'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('owner', 'Owner'), ('member', 'Member'), ('viewer', 'Viewer')], default='member', max_length=20)),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('is_moderator', models.BooleanField()),
                ('is_administrator', models.BooleanField()),
                ('is_owner', models.BooleanField()),
                ('is_contributor', models.BooleanField()),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='project.project')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'project')},
            },
        ),
    ]
