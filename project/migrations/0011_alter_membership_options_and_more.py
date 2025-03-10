# Generated by Django 5.1.4 on 2025-03-08 17:53

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0010_membership'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='membership',
            options={'permissions': [('can_moderate_comments', 'Can moderate comments'), ('can_approve_connections', 'Can approve project connections'), ('can_edit_project', 'Can edit project details'), ('can_add_members', 'Can add members to project'), ('can_remove_members', 'Can remove members from project'), ('can_view_analytics', 'Can view project analytics')]},
        ),
        migrations.AddField(
            model_name='membership',
            name='custom_permissions',
            field=models.JSONField(blank=True, default=dict, help_text='Custom permission overrides for this membership'),
        ),
        migrations.AddField(
            model_name='project',
            name='allow_anonymous_comments',
            field=models.BooleanField(default=True, help_text='Allow non-logged-in users to comment'),
        ),
        migrations.AddField(
            model_name='project',
            name='require_comment_approval',
            field=models.BooleanField(default=False, help_text='Require comments to be approved by moderators before being visible'),
        ),
        migrations.AlterField(
            model_name='connection',
            name='added_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='added_connections', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='connection',
            name='moderated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='moderated_connections', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='membership',
            name='is_administrator',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='membership',
            name='is_contributor',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='membership',
            name='is_moderator',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='membership',
            name='is_owner',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='membership',
            name='role',
            field=models.CharField(choices=[('ADMIN', 'Administrator'), ('MODERATOR', 'Moderator'), ('CONTRIBUTOR', 'Contributor'), ('SUPPORTER', 'Supporter'), ('VIEWER', 'Viewer'), ('CURATOR', 'Curator'), ('MENTOR', 'Mentor'), ('STAKEHOLDER', 'Stakeholder')], default='VIEWER', max_length=20),
        ),
        migrations.AlterField(
            model_name='project',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_projects', to=settings.AUTH_USER_MODEL),
        ),
    ]
