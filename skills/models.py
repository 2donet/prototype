from django.db import models
from django.core.exceptions import ValidationError

class Skill(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def clean(self):
        # Check for case-insensitive duplicates
        existing_skill = Skill.objects.filter(name__iexact=self.name).exclude(pk=self.pk).first()
        if existing_skill:
            raise ValidationError(f"A skill with the name '{existing_skill.name}' already exists. Use the existing skill instead.")

    def save(self, *args, **kwargs):
        self.name = self.name.title()  # Enforce title case
        self.full_clean()  # This will call clean() method
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_skill(cls, name):
        """Helper method to get existing skill or create new one"""
        try:
            return cls.objects.get(name__iexact=name.strip())
        except cls.DoesNotExist:
            return cls.objects.create(name=name.strip().title())

    def __str__(self):
        return self.name