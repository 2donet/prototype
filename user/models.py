from django.db import models
from django.conf import settings
from imagekit.models import ProcessedImageField, ImageSpecField
from imagekit.processors import ResizeToFill, Adjust
from imagekit import ImageSpec
from pilkit.processors import ResizeToFill as PilkitResizeToFill
import os
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
    website = models.URLField(blank=True)
    
    # Use ProcessedImageField instead of ImageField to process and store only the processed version
    avatar = ProcessedImageField(
        upload_to='avatars/',
        processors=[ResizeToFill(400, 400)],  # Main avatar size
        format='WEBP',
        options={'quality': 85},
        blank=True,
        null=True
    )
    
    # Generate smaller variants from the processed avatar
    avatar_thumbnail = ImageSpecField(
        source='avatar',
        processors=[ResizeToFill(150, 150)],
        format='WEBP',
        options={'quality': 85}
    )
    
    avatar_small = ImageSpecField(
        source='avatar',
        processors=[ResizeToFill(50, 50)],
        format='WEBP',
        options={'quality': 80}
    )

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def delete(self, *args, **kwargs):
        # Delete avatar file when profile is deleted
        if self.avatar:
            if os.path.isfile(self.avatar.path):
                os.remove(self.avatar.path)
        super().delete(*args, **kwargs)
    
class Post(models.Model):
    # name = post's title
    name = models.CharField(max_length=128) 
    # date = post's publish date
    date = models.DateTimeField(auto_now_add=True)
    desc = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",  # Changed related_name to plural
        db_index=True
    )

    def __str__(self):
        return self.name

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

        