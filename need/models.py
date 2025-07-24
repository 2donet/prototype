from django.db import models
from utils.permissions import user_has_project_permission
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
User = get_user_model()

NEED_STATUSES = [
    ('pending', 'Pending'),
    ('in_progress', 'In Progress'),
    ('fulfilled', 'Fulfilled'),
    ('canceled', 'Canceled'),
]
VISIBILITY_CHOICES = [
    ('public', 'Public'),
    ('members', 'Project Members Only'),
    ('admins', 'Admins Only'),
]


class Need(models.Model):
    name = models.CharField(max_length=50)
    desc = models.TextField("description")
    priority = models.IntegerField(default=0, null=False, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_index=True,
        related_name="need_added_by"
    )
    estimated_time = models.DurationField(blank=True, null=True, help_text="Estimated time to fulfill this need")
    actual_time = models.DurationField(blank=True, null=True, help_text="Actual time spent fulfilling this need")
    deadline = models.DateTimeField(blank=True, null=True, help_text="Deadline for this need")
    
    resources = models.TextField(blank=True, null=True, help_text="Resources required to fulfill this need")
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Estimated cost to fulfill")
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Actual cost incurred")
    
    depends_on = models.ManyToManyField(
        'self', symmetrical=False, blank=True,
        help_text="Other needs this one depends on",
        related_name='dependents'
    )

    previous_version = models.ForeignKey(
        'self', blank=True, null=True, on_delete=models.SET_NULL,
        related_name='newer_versions'
    )
    related_needs = models.ManyToManyField('self', symmetrical=True, blank=True, 
                                      help_text="Other related needs")
    progress = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)],
                             help_text="Completion percentage (0-100)")
    completion_notes = models.TextField(blank=True, null=True, help_text="Notes about completion")
    completed_by = models.ForeignKey( settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_index=True,
        related_name="satisfied_by"
    )
    completed_date = models.DateTimeField(blank=True, null=True)

    documentation_url = models.URLField(blank=True, null=True, help_text="Link to relevant documentation")


    # New fields
    status = models.CharField(max_length=20, choices=NEED_STATUSES, default='pending')
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    
    to_project = models.ForeignKey("project.Project", blank=True, null=True, on_delete=models.CASCADE)
    to_task = models.ForeignKey("task.Task", blank=True, null=True, on_delete=models.CASCADE)
    custom_fields = models.JSONField(default=dict, blank=True, 
                               help_text="Additional custom fields in JSON format")
    version = models.PositiveIntegerField(default=1)
    
    is_current = models.BooleanField(default=True)
    is_remote = models.BooleanField(default=False, help_text="Can this need be fulfilled remotely?")
    is_stationary = models.BooleanField(default=False, help_text="Is this need location-dependent (stationary)?")

    required_skills = models.ManyToManyField('skills.Skill', blank=True,
                                       help_text="Skills required to fulfill this need")
    skill_level = models.CharField(max_length=20, blank=True, null=True,
                             choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'),
                                      ('advanced', 'Advanced'), ('expert', 'Expert')])
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
    
    def update_progress(self, new_progress, user=None, notes=None):
        """Update progress with validation and history tracking"""
        if not 0 <= new_progress <= 100:
            raise ValueError("Progress must be between 0 and 100")
        
        self.progress = new_progress
        if new_progress == 100:
            self.status = 'fulfilled'
            self.completed_by = user
            self.completed_date = timezone.now()
        self.save()
    def log_time(self, duration, user):
        """Log time spent on this need"""
        TimeLog.objects.create(
            need=self,
            user=user,
            duration=duration,
            logged_at=timezone.now()
        )
        self.actual_time = (self.actual_time or timedelta()) + duration
        self.save()

    def check_dependencies_met(self):
        """Check if all dependent needs are fulfilled"""
        return not self.depends_on.filter(status__in=['pending', 'in_progress']).exists()
    def match_volunteers_by_skills(self):
        """Find users with matching skills for this need"""
        if not self.required_skills.exists():
            return User.objects.none()

        return User.objects.filter(
            skills__in=self.required_skills.all()
        ).distinct().order_by('-skill_level')
    def user_can_view(self, user):
        """Check if user can view this need"""
        if self.visibility == 'public':
            return True
        if not user.is_authenticated:
            return False
        if self.visibility == 'members':
            return self.to_project and self.to_project.user_can_view(user)
        if self.visibility == 'admins':
            return self.to_project and self.to_project.user_can_moderate(user)
        return False

    def user_can_assign(self, user):
        """Check if user can assign this need to others"""
        if not user.is_authenticated:
            return False
        if user.is_superuser or user == self.created_by:
            return True
        if self.to_project:
            return user_has_project_permission(user, self.to_project, 'can_add_members')
        return False

    def user_can_log_time(self, user):
        """Check if user can log time against this need"""
        if not user.is_authenticated:
            return False
        if user.is_superuser or user == self.created_by:
            return True
        if self.assignments.filter(user=user, status='active').exists():
            return True
        if self.to_project:
            return user_has_project_permission(user, self.to_project, 'can_contribute')
        return False
    def __str__(self):
        return self.name
    


class TimeLog(models.Model):
    need = models.ForeignKey(Need, on_delete=models.CASCADE, related_name='time_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)    
    duration = models.DurationField(validators=[MinValueValidator(timedelta(seconds=1))])
    logged_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

class NeedHistory(models.Model):
    need = models.ForeignKey(Need, on_delete=models.CASCADE, related_name='history')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)    
    changed_at = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField()  # Stores field changes
    change_reason = models.TextField(blank=True, null=True)


class NeedAssignment(models.Model):
    need = models.ForeignKey(Need, on_delete=models.CASCADE, related_name='assignments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_assigned')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='assigned_by')

    assigned_at = models.DateTimeField(auto_now_add=True)
    role = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, default='active')