from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType

class IntroManager(models.Manager):
    def published_relations(self):
        """Get intros with published relationships"""
        return self.filter(relations__status=IntroRelation.StatusChoices.PUBLISHED).distinct()
    
    def for_user(self, user):
        return self.filter(by_user=user)
    
    def drafts(self):
        return self.filter(status=self.model.StatusChoices.DRAFT)
    
    def visible_to_user(self, user):
        """Get intros visible to a specific user based on visibility rules"""
        if not user or not user.is_authenticated:
            return self.filter(visibility='public', status=self.model.StatusChoices.PUBLISHED)
        
        # Authenticated users can see public and logged_in intros
        queryset = self.filter(
            models.Q(visibility__in=['public', 'logged_in'], status=self.model.StatusChoices.PUBLISHED) |
            models.Q(by_user=user)  # Always see own intros
        )
        
        # Add restricted intros if user has project membership
        if hasattr(user, 'membership_set'):
            user_project_ids = user.membership_set.values_list('project_id', flat=True)
            queryset = queryset | self.filter(
                main_project_id__in=user_project_ids,
                visibility='restricted',
                status=self.model.StatusChoices.PUBLISHED
            )
        
        return queryset.distinct()

class Intro(models.Model):
    # Basic information
    name = models.CharField(max_length=200, help_text="Title of the introduction")
    summary = models.CharField(max_length=500, help_text="Brief summary (used in listings and previews)")
    desc = models.TextField(help_text="Full detailed description/content")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Visibility settings (copied from Project model)
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('logged_in', 'Only Logged-In Users'),
        ('restricted', 'Restricted (Project Members Only)'),
        ('private', 'Private (Author Only)'),
    ]
    
    visibility = models.CharField(
        max_length=20, 
        choices=VISIBILITY_CHOICES, 
        default='public',
        help_text="Who can view this introduction"
    )
    
    # Context and organization  
    main_project = models.ForeignKey(
        'project.Project',
        on_delete=models.CASCADE,
        related_name='contextual_intros',
        null=True,
        blank=True,
        help_text="Main project context for organizational purposes"
    )
    
    # User and permissions
    by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='intros_created',
        help_text="User who created this intro"
    )
    
    # Ordering and display
    order = models.IntegerField(
        default=0, 
        help_text="Display order (higher numbers appear first)"
    )
    
    # Status workflow
    class StatusChoices(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        UNDER_REVIEW = 'under_review', 'Under Review'
        REJECTED = 'rejected', 'Rejected'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'
    
    status = models.CharField(
        max_length=15,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        help_text="Current status of this introduction"
    )
    
    # Type classification
    class TypeChoices(models.TextChoices):
        OVERVIEW = 'overview', 'Overview'
        CONTEXT = 'context', 'Context'
        BACKGROUND = 'background', 'Background'
        GUIDE = 'guide', 'Guide'
        SUMMARY = 'summary', 'Summary'
    
    intro_type = models.CharField(
        max_length=20,
        choices=TypeChoices.choices,
        default=TypeChoices.OVERVIEW,
        help_text="Type of introduction this represents"
    )
    
    # Engagement tracking
    view_count = models.PositiveIntegerField(default=0, help_text="Number of times viewed")
    
    # Custom manager
    objects = IntroManager()
    
    def clean(self):
        """Validate intro data"""
        super().clean()
        
        # Validate visibility and main_project relationship
        if self.visibility == 'restricted' and not self.main_project:
            raise ValidationError("Restricted intros must have a main project specified")
    
    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation on save
        super().save(*args, **kwargs)
    
    def get_related_entities(self):
        """Get all entities this intro is related to"""
        relations = self.relations.select_related(
            'to_task', 'to_project', 'to_need', 'to_problem', 'to_plan'
        ).all()
        
        entities = []
        for relation in relations:
            entity = relation.get_related_entity()
            if entity:
                entities.append({
                    'entity': entity,
                    'type': relation.get_entity_type(),
                    'status': relation.status,
                    'relation_id': relation.id,
                })
        return entities
    
    def get_published_relations(self):
        """Get only published relationships"""
        return self.relations.filter(
            status=IntroRelation.StatusChoices.PUBLISHED
        ).select_related('to_task', 'to_project', 'to_need', 'to_problem', 'to_plan')
    
    def can_edit(self, user):
        """Check if user can edit this intro"""
        if not user or not user.is_authenticated:
            return False
        
        # Creator can always edit
        if user == self.by_user:
            return True
        
        # Project admins/moderators can edit if intro belongs to their project
        if self.main_project:
            from project.models import Membership
            return Membership.objects.filter(
                project=self.main_project,
                user=user,
                is_administrator=True
            ).exists() or Membership.objects.filter(
                project=self.main_project,
                user=user, 
                is_moderator=True
            ).exists()
        
        return False
    
    def can_view(self, user):
        """Check if user can view this intro"""
        # Check intro's own status first
        if self.status != self.StatusChoices.PUBLISHED:
            # Only creator and project admins can view non-published intros
            if not user or not user.is_authenticated:
                return False
            if user == self.by_user:
                return True
            if self.main_project:
                from project.models import Membership
                return Membership.objects.filter(
                    project=self.main_project,
                    user=user,
                    is_administrator=True
                ).exists() or Membership.objects.filter(
                    project=self.main_project,
                    user=user,
                    is_moderator=True
                ).exists()
            return False
        
        # For published intros, check visibility
        if self.visibility == 'public':
            return True
        elif self.visibility == 'logged_in' and user and user.is_authenticated:
            return True
        elif self.visibility == 'restricted' and user and user.is_authenticated:
            if user == self.by_user:
                return True
            if self.main_project:
                from project.models import Membership
                return Membership.objects.filter(
                    project=self.main_project,
                    user=user
                ).exists()
        elif self.visibility == 'private' and user and user.is_authenticated:
            return user == self.by_user
        
        return False
    
    def can_link_to_entity(self, entity, user):
        """Check if user can create relationships between this intro and an entity"""
        if not user or not user.is_authenticated:
            return False
            
        # Must be able to view the intro
        if not self.can_view(user):
            return False
        
        # Check entity permissions based on type
        entity_project = None
        if hasattr(entity, 'to_project'):
            entity_project = entity.to_project
        elif hasattr(entity, '__class__') and entity.__class__.__name__ == 'Project':
            entity_project = entity
        
        if entity_project:
            # Check if user can contribute to the entity's project
            if hasattr(entity_project, 'user_can_contribute'):
                return entity_project.user_can_contribute(user)
        
        return False
    
    def increment_view_count(self):
        """Safely increment view count"""
        from django.db.models import F
        self.__class__.objects.filter(pk=self.pk).update(view_count=F('view_count') + 1)
    
    def get_absolute_url(self):
        """Get URL for this intro"""
        return reverse('intros:detail', kwargs={'pk': self.pk})
    
    def get_edit_url(self):
        """Get edit URL for this intro"""
        return reverse('intros:edit', kwargs={'pk': self.pk})
    
    @property
    def is_published(self):
        return self.status == self.StatusChoices.PUBLISHED
    
    @property
    def is_draft(self):
        return self.status == self.StatusChoices.DRAFT
    
    def __str__(self):
        entities = self.get_related_entities()
        if entities:
            entity_names = [f"{e['type']}" for e in entities[:2]]
            suffix = f" ({', '.join(entity_names)}{'...' if len(entities) > 2 else ''})"
        else:
            suffix = ""
        return f"{self.name}{suffix}"

    class Meta:
        verbose_name = "Introduction"
        verbose_name_plural = "Introductions"
        ordering = ['-order', '-created_at']
        
        indexes = [
            models.Index(fields=['status', 'visibility', 'created_at']),
            models.Index(fields=['by_user', 'status']),
            models.Index(fields=['main_project', 'status', 'visibility']),
            models.Index(fields=['order', 'created_at']),
        ]
        
        constraints = [
            models.CheckConstraint(
                check=models.Q(order__gte=0),
                name='intro_positive_order'
            ),
            models.CheckConstraint(
                check=models.Q(view_count__gte=0),
                name='intro_positive_view_count'
            ),
        ]


class IntroRelation(models.Model):
    """Through model for intro-entity relationships"""
    intro = models.ForeignKey(
        Intro, 
        on_delete=models.CASCADE, 
        related_name='relations'
    )
    
    # Entity relationships (exactly one should be set)
    to_task = models.ForeignKey(
        'task.Task',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Task this intro relates to"
    )
    to_project = models.ForeignKey(
        'project.Project',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Project this intro relates to"
    )
    to_need = models.ForeignKey(
        'need.Need',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Need this intro relates to"
    )
    to_problem = models.ForeignKey(
        'problems.Problem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Problem this intro relates to"
    )
    to_plan = models.ForeignKey(
        'plans.Plan',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Plan this intro relates to"
    )
    
    # Relationship metadata
    class StatusChoices(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'
        UNDER_REVIEW = 'under_review', 'Under Review'
    
    status = models.CharField(
        max_length=15,
        choices=StatusChoices.choices,
        default=StatusChoices.PUBLISHED,  # Default to published as requested
        help_text="Status of this relationship"
    )
    
    linked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='intro_relations_created'
    )
    linked_at = models.DateTimeField(auto_now_add=True)
    
    order = models.IntegerField(
        default=0,
        help_text="Display order within the entity (higher numbers first)"
    )
    
    note = models.TextField(
        blank=True,
        help_text="Optional note about this relationship"
    )
    
    def clean(self):
        """Validate that exactly one relationship is set"""
        super().clean()
        
        relationships = [
            self.to_task, self.to_project, self.to_need, 
            self.to_problem, self.to_plan
        ]
        non_null_count = sum(1 for rel in relationships if rel is not None)
        
        if non_null_count == 0:
            raise ValidationError("Relation must be connected to exactly one entity")
        elif non_null_count > 1:
            raise ValidationError("Relation can only be connected to one entity at a time")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_related_entity(self):
        """Get the entity this relation points to"""
        for field_name in ['to_task', 'to_project', 'to_need', 'to_problem', 'to_plan']:
            obj = getattr(self, field_name)
            if obj:
                return obj
        return None
    
    def get_entity_type(self):
        """Get the type name of the related entity"""
        if self.to_task:
            return 'Task'
        elif self.to_project:
            return 'Project'
        elif self.to_need:
            return 'Need'
        elif self.to_problem:
            return 'Problem'
        elif self.to_plan:
            return 'Plan'
        return 'Unknown'
    
    def get_entity_project(self):
        """Get the project associated with the related entity"""
        entity = self.get_related_entity()
        if not entity:
            return None
            
        if hasattr(entity, 'to_project'):
            return entity.to_project
        elif entity.__class__.__name__ == 'Project':
            return entity
        return None
    
    def can_edit_status(self, user):
        """Check if user can edit this relationship's status"""
        if not user or not user.is_authenticated:
            return False
        
        # Creator can edit
        if user == self.linked_by:
            return True
        
        # Project admins/moderators can edit
        entity_project = self.get_entity_project()
        if entity_project:
            from project.models import Membership
            return Membership.objects.filter(
                project=entity_project,
                user=user
            ).filter(
                models.Q(is_administrator=True) | models.Q(is_moderator=True)
            ).exists()
        
        return False
    
    def get_absolute_url(self):
        """Get URL to manage this relationship"""
        return reverse('intros:relation_detail', kwargs={
            'intro_id': self.intro.pk,
            'relation_id': self.pk
        })
    
    def __str__(self):
        entity = self.get_related_entity()
        return f"{self.intro.name} → {entity} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Introduction Relationship"
        verbose_name_plural = "Introduction Relationships"
        ordering = ['-order', '-linked_at']
        
        indexes = [
            models.Index(fields=['intro', 'status']),
            models.Index(fields=['to_project', 'status']),
            models.Index(fields=['to_task', 'status']),
            models.Index(fields=['to_need', 'status']),
            models.Index(fields=['to_problem', 'status']),
            models.Index(fields=['to_plan', 'status']),
            models.Index(fields=['linked_by', 'status']),
        ]
        
        constraints = [
            # Prevent duplicate relationships
            models.UniqueConstraint(
                fields=['intro', 'to_task'],
                condition=models.Q(to_task__isnull=False),
                name='unique_intro_task_relation'
            ),
            models.UniqueConstraint(
                fields=['intro', 'to_project'],
                condition=models.Q(to_project__isnull=False),
                name='unique_intro_project_relation'
            ),
            models.UniqueConstraint(
                fields=['intro', 'to_need'],
                condition=models.Q(to_need__isnull=False),
                name='unique_intro_need_relation'
            ),
            models.UniqueConstraint(
                fields=['intro', 'to_problem'],
                condition=models.Q(to_problem__isnull=False),
                name='unique_intro_problem_relation'
            ),
            models.UniqueConstraint(
                fields=['intro', 'to_plan'],
                condition=models.Q(to_plan__isnull=False),
                name='unique_intro_plan_relation'
            ),
            models.CheckConstraint(
                check=models.Q(order__gte=0),
                name='relation_positive_order'
            ),
        ]


class LinkingIssue(models.Model):
    """Handle cases where users try to create duplicate relationships"""
    intro = models.ForeignKey(
        Intro,
        on_delete=models.CASCADE,
        related_name='linking_issues'
    )
    
    # The entity they tried to link to
    attempted_target_type = models.CharField(
        max_length=20,
        choices=[
            ('task', 'Task'),
            ('project', 'Project'),
            ('need', 'Need'),
            ('problem', 'Problem'),
            ('plan', 'Plan'),
        ]
    )
    attempted_target_id = models.PositiveIntegerField()
    
    # User who attempted the linking
    attempted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='linking_issues_created'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    
    # Future expansion fields
    resolution_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linking_issues_resolved'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def get_attempted_target(self):
        """Get the target entity that was attempted to be linked"""
        from django.apps import apps
        
        model_mapping = {
            'task': ('task', 'Task'),
            'project': ('project', 'Project'),
            'need': ('need', 'Need'),
            'problem': ('problems', 'Problem'),
            'plan': ('plans', 'Plan'),
        }
        
        if self.attempted_target_type in model_mapping:
            app_label, model_name = model_mapping[self.attempted_target_type]
            model = apps.get_model(app_label, model_name)
            try:
                return model.objects.get(pk=self.attempted_target_id)
            except model.DoesNotExist:
                return None
        return None
    
    def __str__(self):
        target = self.get_attempted_target()
        return f"Linking issue: {self.intro.name} → {target} (by {self.attempted_by.username})"

    class Meta:
        verbose_name = "Linking Issue"
        verbose_name_plural = "Linking Issues"
        ordering = ['-created_at']
        
        indexes = [
            models.Index(fields=['intro', 'resolved']),
            models.Index(fields=['attempted_by', 'resolved']),
            models.Index(fields=['created_at']),
        ]