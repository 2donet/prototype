
import os
import hashlib
from django.db import models
from django.conf import settings
from django.core.files.storage import default_storage
from imagekit.models import ProcessedImageField, ImageSpecField
from imagekit.processors import ResizeToFill
from PIL import Image


def generate_avatar_upload_path(instance, filename):
    """
    Generate hash-based filename for avatar uploads
    """
    try:
        # Read the file content to generate hash
        file_content = instance.read()
        
        # Generate SHA256 hash from file content (first 16 chars)
        file_hash = hashlib.sha256(file_content).hexdigest()[:16]
        
        # Reset file pointer after reading
        instance.seek(0)
        
        # Always use .webp extension since we're converting
        return f'avatars/{file_hash}.webp'
        
    except Exception as e:
        # Fallback to timestamp-based naming if hash fails
        import time
        timestamp = int(time.time())
        return f'avatars/fallback_{timestamp}.webp'


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
    
    # Hash-based avatar with ProcessedImageField
    avatar = ProcessedImageField(
        upload_to=generate_avatar_upload_path,
        processors=[ResizeToFill(400, 400)],
        format='WEBP',
        options={
            'quality': 85,
            'optimize': True,
            'progressive': True,
        },
        blank=True,
        null=True
    )
    
    # Generate smaller variants from the processed avatar
    avatar_thumbnail = ImageSpecField(
        source='avatar',
        processors=[ResizeToFill(150, 150)],
        format='WEBP',
        options={'quality': 85, 'optimize': True}
    )
    
    avatar_small = ImageSpecField(
        source='avatar',
        processors=[ResizeToFill(50, 50)],
        format='WEBP',
        options={'quality': 80, 'optimize': True}
    )

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def avatar_hash(self):
        """Get the hash portion of the avatar filename"""
        if self.avatar and self.avatar.name:
            filename = os.path.basename(self.avatar.name)
            return filename.split('.')[0]  # Return hash without extension
        return None
    
    def get_avatar_info(self):
        """Get detailed avatar information"""
        if not self.has_avatar():
            return None
            
        try:
            return {
                'hash': self.avatar_hash,
                'filename': os.path.basename(self.avatar.name),
                'size': self.avatar.size,
                'url': self.avatar.url,
                'path': self.avatar.path if hasattr(self.avatar, 'path') else None,
            }
        except Exception:
            return None
    
    def has_avatar(self):
        """Check if user has an uploaded avatar"""
        return bool(self.avatar and self.avatar.name)
    
    def cleanup_old_avatar(self, old_avatar_field):
        """Clean up old avatar files"""
        if not old_avatar_field:
            return
            
        try:
            # Delete the physical file
            if hasattr(old_avatar_field, 'path') and os.path.isfile(old_avatar_field.path):
                os.remove(old_avatar_field.path)
                
            # Clean up ImageKit generated files
            old_hash = os.path.basename(old_avatar_field.name).split('.')[0]
            cache_dir = os.path.join(settings.MEDIA_ROOT, 'CACHE', 'images', 'avatars')
            
            if os.path.exists(cache_dir):
                for cache_file in os.listdir(cache_dir):
                    if cache_file.startswith(old_hash):
                        cache_file_path = os.path.join(cache_dir, cache_file)
                        try:
                            os.remove(cache_file_path)
                        except OSError:
                            pass  # File might already be gone
                            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to cleanup old avatar: {e}")
    
    def save(self, *args, **kwargs):
        """Override save to handle old avatar cleanup"""
        old_avatar = None
        
        # Get old avatar for cleanup if this is an update
        if self.pk:
            try:
                old_profile = UserProfile.objects.get(pk=self.pk)
                if old_profile.avatar != self.avatar:
                    old_avatar = old_profile.avatar
            except UserProfile.DoesNotExist:
                pass
        
        # Save the profile
        super().save(*args, **kwargs)
        
        # Clean up old avatar after successful save
        if old_avatar:
            self.cleanup_old_avatar(old_avatar)
    
    def delete(self, *args, **kwargs):
        """Clean up avatar files when profile is deleted"""
        if self.avatar:
            self.cleanup_old_avatar(self.avatar)
        super().delete(*args, **kwargs)

class User(models.Model):
    name = models.CharField(("Username"), max_length=50)

    def __str__(self):
        return self.name
    
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

        