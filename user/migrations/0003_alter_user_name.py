# Generated by Django 5.1.4 on 2024-12-25 11:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_group_person_membership_group_members'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='name',
            field=models.CharField(max_length=50, verbose_name='Username'),
        ),
    ]