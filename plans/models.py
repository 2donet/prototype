from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

class Plan(models.Model):
    name = models.CharField(max_length=200)
    desc = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_plans'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Template functionality for future use
    is_template = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
    
    def get_main_project(self):
        """Get the main project this plan is associated with through suggestions"""
        suggestion = self.suggestions.select_related(
            'content_type'
        ).prefetch_related('content_object').first()
        
        if suggestion and suggestion.content_object:
            content_obj = suggestion.content_object
            
            # If content is a Project, check if it has a main_project
            if hasattr(content_obj, 'main_project'):
                return content_obj.main_project or content_obj
            # If content is a Task or Need, get their main_project
            elif hasattr(content_obj, 'to_project'):
                project = content_obj.to_project
                return project.main_project if project and project.main_project else project
                
        return None
    
    def user_can_view(self, user):
        """Check if user can view this plan"""
        if not user.is_authenticated:
            return False
            
        # Plan creator can always view
        if self.created_by == user:
            return True
            
        # Check permissions through associated content
        main_project = self.get_main_project()
        if main_project:
            return main_project.user_can_view(user)
            
        return False
    
    def user_can_edit(self, user):
        """Check if user can edit this plan"""
        if not user.is_authenticated:
            return False
            
        # Plan creator can always edit
        if self.created_by == user:
            return True
            
        # Check admin permissions through associated content
        main_project = self.get_main_project()
        if main_project:
            from utils.permissions import user_has_project_permission
            return user_has_project_permission(user, main_project, 'can_admin')
            
        return False


class Step(models.Model):
    plan = models.ForeignKey(Plan, related_name='steps', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    desc = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.name} (Step of {self.plan.name})"


class PlanSuggestionStatus(models.TextChoices):
    PENDING = 'pending', 'Pending Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    WITHDRAWN = 'withdrawn', 'Withdrawn'


class PlanSuggestion(models.Model):
    """Links plans to content (Projects, Tasks, Needs) with approval workflow"""
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='suggestions')
    
    # Generic foreign key to link to any content type
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Workflow fields
    status = models.CharField(
        max_length=20, 
        choices=PlanSuggestionStatus.choices, 
        default=PlanSuggestionStatus.PENDING
    )
    
    # User management
    suggested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='plan_suggestions'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_plan_suggestions'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    suggestion_note = models.TextField(blank=True, help_text="Why this plan is suggested")
    review_note = models.TextField(blank=True, help_text="Admin's review comments")
    
    class Meta:
        unique_together = ('plan', 'content_type', 'object_id')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.plan.name} suggested for {self.content_object}"
    
    def approve(self, user, note=""):
        """Approve the suggestion"""
        self.status = PlanSuggestionStatus.APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_note = note
        self.save()
    
    def reject(self, user, note=""):
        """Reject the suggestion"""
        self.status = PlanSuggestionStatus.REJECTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_note = note
        self.save()
    
    def withdraw(self):
        """Allow suggester to withdraw their suggestion"""
        self.status = PlanSuggestionStatus.WITHDRAWN
        self.reviewed_at = timezone.now()
        self.save()
    
    def get_main_project(self):
        """Get the main project this suggestion relates to"""
        content_obj = self.content_object
        
        if not content_obj:
            return None
            
        # If content is a Project
        if content_obj.__class__.__name__ == 'Project':
            return content_obj.main_project or content_obj
        
        # If content is Task or Need
        elif hasattr(content_obj, 'to_project'):
            project = content_obj.to_project
            return project.main_project if project and project.main_project else project
            
        return None
    
    def user_can_review(self, user):
        """Check if user can review this suggestion (admin only)"""
        if not user.is_authenticated:
            return False
            
        main_project = self.get_main_project()
        if main_project:
            from utils.permissions import user_has_project_permission
            return user_has_project_permission(user, main_project, 'can_admin')
            
        return False
    
    def user_can_view(self, user):
        """Check if user can view this suggestion"""
        if not user.is_authenticated:
            return False
            
        # Suggester can always view
        if self.suggested_by == user:
            return True
            
        # Check project membership
        main_project = self.get_main_project()
        if main_project:
            return main_project.user_can_view(user)
            
        return False