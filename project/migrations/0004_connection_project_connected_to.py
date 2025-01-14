# Generated by Django 5.1.4 on 2025-01-14 16:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0003_project_area_project_collaboration_mode_and_more'),
        ('user', '0004_alter_membership_unique_together'),
    ]

    operations = [
        migrations.CreateModel(
            name='Connection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('type', models.CharField(choices=[('child', 'Child'), ('parent', 'Parent'), ('linked', 'Linked')], max_length=10)),
                ('added_date', models.DateTimeField(auto_now_add=True)),
                ('moderated_date', models.DateTimeField(blank=True, null=True)),
                ('added_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='added_connections', to='user.user')),
                ('from_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outgoing_connections', to='project.project')),
                ('moderated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='moderated_connections', to='user.user')),
                ('to_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incoming_connections', to='project.project')),
            ],
            options={
                'unique_together': {('from_project', 'to_project', 'type')},
            },
        ),
        migrations.AddField(
            model_name='project',
            name='connected_to',
            field=models.ManyToManyField(through='project.Connection', to='project.project'),
        ),
    ]
