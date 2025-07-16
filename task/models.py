from django.db import models
from django.utils import timezone
from django.conf import settings

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

    def __str__(self):
        return self.name