from django.db import models
from django.utils import timezone
from django.conf import settings
from skills.models import Skill

class Task(models.Model):
    name = models.CharField(max_length=50)
    desc = models.TextField("description")
    priority = models.IntegerField(null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='created_tasks'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    contributions = models.JSONField(null=True)
    
    to_project = models.ForeignKey("project.Project", blank=True, null=True, on_delete=models.CASCADE)
    to_task = models.ForeignKey("task.Task", blank=True, null=True, on_delete=models.CASCADE)
    main_project = models.ForeignKey("project.Project", null=True, blank=True, on_delete=models.CASCADE, related_name='all_tasks')
    # Skills relationship
    skills = models.ManyToManyField('skills.Skill', blank=True)
    
    # New fields for permission management
    allow_anonymous_comments = models.BooleanField(
        default=True,
        help_text="Allow non-logged-in users to comment"
    )
    require_comment_approval = models.BooleanField(
        default=False,
        help_text="Require comments to be approved by moderators before being visible"
    )

    def __str__(self):
        return self.name

    def add_skill(self, skill_name):
        """Adds a skill to the task, ensuring max 20 skills"""
        skill, created = Skill.objects.get_or_create(name=skill_name.title())
        if self.skills.count() < 20:
            self.skills.add(skill)
        else:
            raise ValueError("A task can have a maximum of 20 skills.")