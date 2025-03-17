from django.db import models
from utils.permissions import user_has_project_permission

class Need(models.Model):
    name = models.CharField(max_length=50)
    desc = models.TextField("description")
    priority = models.IntegerField(default=0, null=False, blank=True)
    created_by = models.ForeignKey("user.User", on_delete=models.CASCADE)
    
    # New fields
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('fulfilled', 'Fulfilled'),
        ('canceled', 'Canceled')
    ], default='pending')
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    tags = models.TextField(blank=True, null=True, help_text="Comma-separated tags")
    visibility = models.CharField(max_length=20, choices=[
        ('public', 'Public'),
        ('members', 'Project Members Only'),
        ('admins', 'Admins Only')
    ], default='public')
    
    to_project = models.ForeignKey("project.Project", blank=True, null=True, on_delete=models.CASCADE)
    to_task = models.ForeignKey("task.Task", blank=True, null=True, on_delete=models.CASCADE)
    
    def get_parent(self):
        """Return the parent object (project or task)"""
        return self.to_project or self.to_task
        
    def user_can_edit(self, user):
        """Check if user can edit this need"""
        if not user.is_authenticated:
            return False
            
        if user.is_superuser or user == self.created_by:
            return True
            
        if self.to_project:
            return user_has_project_permission(user, self.to_project, 'can_contribute')
            
        if self.to_task and self.to_task.to_project:
            return user_has_project_permission(user, self.to_task.to_project, 'can_contribute')
            
        return False