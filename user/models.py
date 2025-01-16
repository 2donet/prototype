from django.db import models
from django.conf import settings


# Create your models here.
class User(models.Model):
    name = models.CharField(("Username"), max_length=50)

    def __str__(self):
        return self.name

    # def get_absolute_url(self):
    #     return Ueverse("user_detail", kwargs={"pk": self.pk})

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        db_index=True
    )
    bio = models.TextField(blank=True)    
    location = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
class Person(models.Model):
    name = models.CharField(max_length=128)
    def __str__(self):
        return self.name

class Group(models.Model):
    name = models.CharField(max_length=128)
    members = models.ManyToManyField(Person, through='Membership')
    def __str__(self):
        return self.name

class Membership(models.Model):
    # issue: allows User to have many memberships with one group (e.g., User A can have +10 memberships in group B)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    date_joined = models.DateField()
    invite_reason = models.CharField(max_length=64)
    
    class Meta:
        unique_together = ('person', 'group')  # Prevent duplicate memberships

    def __str__(self):
        person_name = getattr(self.person, 'name')
        group_name = getattr(self.group, 'name')
        return f"{group_name}: {person_name}"

        