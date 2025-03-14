# Generated by Django 5.1.4 on 2025-01-23 10:39

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contribution', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='contribution',
            name='votes_power',
            field=models.IntegerField(blank=True, default=0),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.IntegerField(null=True)),
                ('power', models.IntegerField(null=True)),
                ('by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('to', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='contribution.contribution')),
            ],
        ),
    ]
