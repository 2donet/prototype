from django.db import models
# from django.contrib.auth.models import User
from django.conf import settings
from skills.models import Skill

# Create your models here.
class Project(models.Model):

    name = models.CharField(max_length=50)
    summary = models.TextField("summary", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_index=True
    )
    connected_to = models.ManyToManyField('self', through='Connection', symmetrical=False)




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

    desc = models.TextField("description", blank=True)
    # comment = models.ForeignKey("comment.Comment", blank=True, null=True, on_delete=models.CASCADE)

    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    collaboration_mode = models.CharField(max_length=50, default='volunteering')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)
    area = models.CharField(max_length=255, blank=True, null=True)
    tags = models.TextField(blank=True, null=True, help_text="Comma-separated tags")
    published = models.BooleanField(default=False)



    skills = models.ManyToManyField('skills.Skill', blank=True)  # Allow projects with no skills

    def add_skill(self, skill_name):
        """Adds a skill to the project, ensuring max 20 skills"""
        skill, created = Skill.objects.get_or_create(name=skill_name.title())
        if self.skills.count() < 20:
            self.skills.add(skill)
        else:
            raise ValueError("A project can have a maximum of 20 skills.")
        
    def __str__(self):
        return self.name
    

class Connection(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    TYPE_CHOICES = [
        ('child', 'Child'),
        ('parent', 'Parent'),
        ('linked', 'Linked'),
    ]

    from_project = models.ForeignKey(Project, related_name='outgoing_connections', on_delete=models.CASCADE)
    to_project = models.ForeignKey(Project, related_name='incoming_connections', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    added_by = models.ForeignKey("user.User", related_name='added_connections', on_delete=models.SET_NULL, null=True, blank=True)
    moderated_by = models.ForeignKey("user.User", related_name='moderated_connections', on_delete=models.SET_NULL, null=True, blank=True)
    added_date = models.DateTimeField(auto_now_add=True)
    moderated_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('from_project', 'to_project', 'type')

    def __str__(self):
        return f"{self.from_project.name} -> {self.to_project.name} ({self.type})"


class Membership(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    date_joined = models.DateTimeField(auto_now_add=True)
    is_moderator = models.BooleanField()
    is_administrator = models.BooleanField()
    is_owner = models.BooleanField()
    is_contributor = models.BooleanField()

    class Meta:
        unique_together = ('user', 'project')  # Ensures a user can't be in the same project twice

    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.role})"
