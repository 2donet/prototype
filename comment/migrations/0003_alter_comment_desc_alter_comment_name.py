# Generated by Django 5.1.4 on 2024-12-25 15:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comment', '0002_alter_comment_options_comment_to_membership_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='desc',
            field=models.TextField(verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='comment',
            name='name',
            field=models.CharField(max_length=256, verbose_name='title'),
        ),
    ]
