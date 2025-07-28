from django.db import models
from django.utils import timezone
from django.conf import settings
from skills.models import Skill

class Task(models.Model):
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'), 
        (3, 'High'),
        (4, 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
    ]
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('logged_in', 'Logged-in Users Only'),
        ('restricted', 'Restricted Access'),
    ]

    name = models.CharField(max_length=50)
    desc = models.TextField("description")
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='created_tasks'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True, help_text="Target completion date")
    
    # New status and time tracking fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    estimated_hours = models.PositiveIntegerField(null=True, blank=True, help_text="Estimated hours to complete")
    actual_hours = models.PositiveIntegerField(null=True, blank=True, help_text="Actual hours spent")
    
    # Visibility control (admin-managed)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    
    contributions = models.JSONField(null=True)
    
    to_project = models.ForeignKey("project.Project", blank=True, null=True, on_delete=models.CASCADE)
    to_task = models.ForeignKey("task.Task", blank=True, null=True, on_delete=models.CASCADE)
    main_project = models.ForeignKey("project.Project", null=True, blank=True, on_delete=models.CASCADE, related_name='all_tasks')
    
    # Skills relationship
    skills = models.ManyToManyField('skills.Skill', blank=True)
    
    # Comment permission fields
    allow_anonymous_comments = models.BooleanField(
        default=True,
        help_text="Allow non-logged-in users to comment"
    )
    require_comment_approval = models.BooleanField(
        default=False,
        help_text="Require comments to be approved by moderators before being visible"
    )
    def save(self, *args, **kwargs):
        # If we have a parent task but no project, inherit main_project
        if self.to_task and not self.to_project:
            if self.to_task.main_project:
                self.main_project = self.to_task.main_project
        
        super().save(*args, **kwargs)
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['due_date']),
            models.Index(fields=['visibility']),
        ]

    def __str__(self):
        return self.name

    @property
    def priority_display(self):
        return dict(self.PRIORITY_CHOICES).get(self.priority, 'Medium')
    
    @property
    def priority_class(self):
        """Returns CSS class for priority styling"""
        priority_map = {
            1: 'priority-low',
            2: 'priority-medium', 
            3: 'priority-high',
            4: 'priority-critical'
        }
        return priority_map.get(self.priority, 'priority-medium')
    
    @property
    def status_class(self):
        """Returns CSS class for status styling"""
        status_map = {
            'todo': 'status-todo',
            'in_progress': 'status-progress',
            'review': 'status-review',
            'completed': 'status-complete'
        }
        return status_map.get(self.status, 'status-todo')
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and self.status != 'completed':
            return timezone.now() > self.due_date
        return False
    
    @property 
    def days_until_due(self):
        """Get days until due date"""
        if self.due_date:
            delta = self.due_date - timezone.now()
            return delta.days
        return None

    def add_skill(self, skill_name):
        """Adds a skill to the task, ensuring max 20 skills"""
        skill, created = Skill.objects.get_or_create(name=skill_name.title())
        if self.skills.count() < 20:
            self.skills.add(skill)
        else:
            raise ValueError("A task can have a maximum of 20 skills.")
    
    def get_progress_percentage(self):
        """Calculate progress based on status"""
        progress_map = {
            'todo': 0,
            'in_progress': 50,
            'review': 75,
            'completed': 100
        }
        return progress_map.get(self.status, 0)