# Generated by Django 5.1.4 on 2024-12-25 15:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comment', '0003_alter_comment_desc_alter_comment_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='to_comment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='comment.comment'),
        ),
    ]
