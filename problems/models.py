from django.db import models
from project.models import Project
from task.models import Task
from need.models import Need
from skills.models import Skill
from submissions.models import Submission
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse

class Problem(models.Model):
    name = models.CharField(max_length=200)
    summary = models.TextField(max_length=500, blank=True, null=True)
    desc = models.TextField()
    
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    ]
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=1)
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('pending', 'Pending'),
        ('solved', 'Solved'),
        ('unsolvable', 'Unsolvable'),
        ('closed', 'Closed'),
        ('duplicate', 'Duplicate'),
        ('invalid', 'Invalid'),
        ('in_progress', 'In Progress'),
        ('needs_info', 'Needs More Info'),
        ('reopened', 'Reopened'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('logged_in', 'Logged-in Users Only'),
        ('restricted', 'Restricted Access'),
    ]
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    
    # User relationships
    created_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_problems'
    )
    
    # NEW: Multiple assignment functionality
    assigned_to = models.ManyToManyField(
        'auth.User',
        blank=True,
        related_name='assigned_problems',
        help_text="Users responsible for resolving this problem"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # NEW: Due date and resolution tracking
    due_date = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True, null=True, help_text="Description of how the problem was resolved")
    
    # Related objects (at least one must be set)
    to_project = models.ForeignKey(
        Project,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='problems'
    )
    to_task = models.ForeignKey(
        Task,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='problems'
    )
    to_need = models.ForeignKey(
        Need,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='problems'
    )
    
    # NEW: Skills instead of tags
    skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name='problems',
        help_text="Skills related to this problem"
    )
    
    def clean(self):
        """Ensure at least one relationship is set"""
        if not any([self.to_project, self.to_task, self.to_need]):
            raise ValidationError("Problem must be related to at least one Project, Task, or Need.")
    
    def save(self, *args, **kwargs):
        # Auto-set resolved_at when status changes to solved
        if self.status == 'solved' and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status != 'solved':
            self.resolved_at = None
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('problems:detail', kwargs={'pk': self.pk})
    
    def get_related_object(self):
        """Return the primary related object (project, task, or need)"""
        if self.to_project:
            return self.to_project
        elif self.to_task:
            return self.to_task
        elif self.to_need:
            return self.to_need
        return None
    
    def get_related_object_type(self):
        """Return the type of the related object"""
        if self.to_project:
            return 'project'
        elif self.to_task:
            return 'task'
        elif self.to_need:
            return 'need'
        return None
    
    def is_overdue(self):
        """Check if problem is past due date"""
        if self.due_date and self.status not in ['solved', 'closed', 'unsolvable']:
            return timezone.now() > self.due_date
        return False
    
    def can_be_viewed_by(self, user):
        """Check if user can view this problem based on visibility settings"""
        if self.visibility == 'public':
            return True
        elif self.visibility == 'logged_in':
            return user.is_authenticated
        elif self.visibility == 'restricted':
            # You can customize this logic based on your needs
            return user.is_authenticated and (
                user == self.created_by or 
                user in self.assigned_to.all() or 
                user.is_staff
            )
        return False
    
    def get_assigned_users_display(self):
        """Get comma-separated list of assigned usernames"""
        return ", ".join([user.username for user in self.assigned_to.all()])
    
    def get_skills_display(self):
        """Get comma-separated list of skill names"""
        return ", ".join([skill.name for skill in self.skills.all()])
    
    def assign_user(self, user):
        """Assign a user to this problem"""
        self.assigned_to.add(user)
        # Create activity log
        ProblemActivity.objects.create(
            problem=self,
            user=user,  # or could be the user doing the assignment
            activity_type='assigned',
            desc=f"User {user.username} was assigned to this problem"
        )
    
    def unassign_user(self, user):
        """Unassign a user from this problem"""
        self.assigned_to.remove(user)
        # Create activity log
        ProblemActivity.objects.create(
            problem=self,
            user=user,  # or could be the user doing the unassignment
            activity_type='unassigned',
            desc=f"User {user.username} was unassigned from this problem"
        )
    
    def add_skill(self, skill_name):
        """Add a skill to this problem"""
        skill = Skill.get_or_create_skill(skill_name)
        self.skills.add(skill)
        # Create activity log
        ProblemActivity.objects.create(
            problem=self,
            activity_type='skills_changed',
            desc=f"Skill '{skill.name}' was added to this problem"
        )
        return skill
    
    def can_be_edited_by(self, user):
        """Check if user can edit this problem - inherits from parent object"""
        if not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        if user == self.created_by:
            return True
        if user in self.assigned_to.all():
            return True
        
        # Inherit permissions from parent object
        parent = self.get_related_object()
        if parent:
            if hasattr(parent, 'user_can_contribute'):
                return parent.user_can_contribute(user)
            elif hasattr(parent, 'can_be_edited_by'):
                return parent.can_be_edited_by(user)
        
        return False
    
    def can_be_viewed_by(self, user):
        """Check if user can view this problem - inherits from parent object"""
        if self.visibility == 'public':
            return True
        elif self.visibility == 'logged_in':
            return user.is_authenticated
        elif self.visibility == 'restricted':
            if not user.is_authenticated:
                return False
            if user == self.created_by or user in self.assigned_to.all() or user.is_staff:
                return True
                
        # Inherit permissions from parent object
        parent = self.get_related_object()
        if parent:
            if hasattr(parent, 'user_can_view'):
                return parent.user_can_view(user)
            elif hasattr(parent, 'can_be_viewed_by'):
                return parent.can_be_viewed_by(user)
        
        return False
    
    def can_be_commented_by(self, user):
        """Check if user can comment on this problem - inherits from parent"""
        parent = self.get_related_object()
        if parent and hasattr(parent, 'user_can_comment'):
            return parent.user_can_comment(user)
        
        # Fallback to view permissions
        return self.can_be_viewed_by(user)
    
    def get_status_color(self):
        """Return CSS color class based on status"""
        status_colors = {
            'open': 'var(--information)',
            'pending': 'var(--warning)',
            'solved': 'var(--confirm)',
            'unsolvable': 'var(--danger)',
            'closed': 'var(--text2ndary)',
            'duplicate': 'var(--highlightdark)',
            'invalid': 'var(--danger)',
            'in_progress': 'var(--highlight)',
            'needs_info': 'var(--warning)',
            'reopened': 'var(--risk)',
        }
        return status_colors.get(self.status, 'var(--text)')
    
    def get_priority_color(self):
        """Return CSS color based on priority"""
        priority_colors = {
            1: 'var(--confirm)',      # Low - green
            2: 'var(--warning)',      # Medium - yellow
            3: 'var(--risk)',         # High - pink
            4: 'var(--danger)',       # Critical - red
        }
        return priority_colors.get(self.priority, 'var(--text)')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Problems"
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['due_date']),
            models.Index(fields=['visibility']),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(to_project__isnull=False) |
                    models.Q(to_task__isnull=False) |
                    models.Q(to_need__isnull=False)
                ),
                name='problem_must_have_relation'
            )
        ]


# NEW: Problem comment/activity log model
class ProblemActivity(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    
    ACTIVITY_TYPES = [
        ('created', 'Problem Created'),
        ('status_changed', 'Status Changed'),
        ('assigned', 'Assigned'),
        ('unassigned', 'Unassigned'),
        ('commented', 'Comment Added'),
        ('priority_changed', 'Priority Changed'),
        ('due_date_set', 'Due Date Set'),
        ('due_date_changed', 'Due Date Changed'),
        ('due_date_removed', 'Due Date Removed'),
        ('desc_changed', 'Description Changed'),
        ('skills_changed', 'Skills Changed'),
        ('resolved', 'Problem Resolved'),
    ]
    
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    desc = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.problem.name} - {self.get_activity_type_display()}"
    
    class Meta:
        ordering = ['-created_at']