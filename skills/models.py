from django.db import models
from django.utils.text import slugify

class Skill(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def save(self, *args, **kwargs):
        self.name = self.name.title()  # Enforce title case
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
