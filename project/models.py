from django.db import models
# from django.contrib.auth.models import User

# Create your models here.
class Project(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('logged_in', 'Only Logged-In Users'),
        ('restricted', 'Restricted (Added Users Only)'),
        ('private', 'Private (Author Only)'),
    ]
    STATUS_CHOICES = [
        ('to_do', 'To Do'),
        ('doing', 'Doing'),
        ('done', 'Done'),
    ]

    name = models.CharField(max_length=50)
    summary = models.TextField("summary", blank=True)
    desc = models.TextField("description", blank=True)
    created_by = models.ForeignKey("user.User", on_delete=models.CASCADE)
    # comment = models.ForeignKey("comment.Comment", blank=True, null=True, on_delete=models.CASCADE)

    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    collaboration_mode = models.CharField(max_length=50, default='volunteering')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)
    area = models.CharField(max_length=255, blank=True, null=True)
    tags = models.TextField(blank=True, null=True, help_text="Comma-separated tags")
    published = models.BooleanField(default=False)


    def __str__(self):
        return self.name