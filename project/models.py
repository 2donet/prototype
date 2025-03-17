from django.db import models
from django.conf import settings
from skills.models import Skill
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
User = get_user_model()

class ProjectPermissionGroup(models.TextChoices):
    """Project-specific permission groups"""
    ADMIN = 'ADMIN', 'Administrator'
    MODERATOR = 'MODERATOR', 'Moderator'
    CONTRIBUTOR = 'CONTRIBUTOR', 'Contributor'
    SUPPORTER = 'SUPPORTER', 'Supporter'
    VIEWER = 'VIEWER', 'Viewer'
    CURATOR = 'CURATOR', 'Curator'
    MENTOR = 'MENTOR', 'Mentor'
    STAKEHOLDER = 'STAKEHOLDER', 'Stakeholder'


class Project(models.Model):
    name = models.CharField(max_length=50)
    summary = models.TextField("summary", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, 
        db_index=True, related_name='created_projects'
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
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    collaboration_mode = models.CharField(max_length=50, default='volunteering')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)
    area = models.CharField(max_length=255, blank=True, null=True)
    tags = models.TextField(blank=True, null=True, help_text="Comma-separated tags")
    published = models.BooleanField(default=False)
    skills = models.ManyToManyField('skills.Skill', blank=True)
    
    # New fields for permission management
    allow_anonymous_comments = models.BooleanField(default=True, 
        help_text="Allow non-logged-in users to comment")
    require_comment_approval = models.BooleanField(default=False, 
        help_text="Require comments to be approved by moderators before being visible")
    
    def add_skill(self, skill_name):
        """Adds a skill to the project, ensuring max 20 skills"""
        skill, created = Skill.objects.get_or_create(name=skill_name.title())
        if self.skills.count() < 20:
            self.skills.add(skill)
        else:
            raise ValueError("A project can have a maximum of 20 skills.")
    
    def add_member(self, user, role='VIEWER'):
        """Add a user to the project with specified role"""
        membership, created = Membership.objects.get_or_create(
            user=user,
            project=self,
            defaults={
                'role': role,
                'is_administrator': role == 'ADMIN',
                'is_moderator': role in ['ADMIN', 'MODERATOR'],
                'is_contributor': role in ['ADMIN', 'CONTRIBUTOR', 'MENTOR'],
                'is_owner': user == self.created_by
            }
        )
        
        if not created:
            # Update existing membership with new role
            membership.role = role
            membership.is_administrator = role == 'ADMIN'
            membership.is_moderator = role in ['ADMIN', 'MODERATOR']
            membership.is_contributor = role in ['ADMIN', 'CONTRIBUTOR', 'MENTOR']
            membership.save()
        
        return membership
    
    def get_members_by_role(self, role):
        """Get all users with a specific role in this project"""
        return User.objects.filter(
            membership__project=self,
            membership__role=role
        )
    
    def user_can_moderate_comments(self, user):
        """Check if user has comment moderation permissions"""
        if not user.is_authenticated:
            return False
            
        # Site-wide admin or moderator
        if user.is_superuser or user.is_staff:
            return True
            
        # Project-specific admin or moderator
        return Membership.objects.filter(
            project=self,
            user=user,
            is_moderator=True
        ).exists()
    
    def user_can_comment(self, user):
        """Determine if a user can comment on this project"""
        # If anonymous comments are allowed, anyone can comment
        if self.allow_anonymous_comments and self.visibility == 'public':
            return True
            
        # Check if user is authenticated
        if not user.is_authenticated:
            return False
            
        # For logged_in visibility, all authenticated users can comment
        if self.visibility == 'logged_in':
            return True
            
        # For restricted and private, check membership
        return Membership.objects.filter(project=self, user=user).exists()
    def user_can_contribute(self, user):
        if not user.is_authenticated:
            return False
        
    # Project owners and admins can contribute
        if user == self.created_by:
            return True
            # Check membership
        membership = Membership.objects.filter(project=self, user=user).first()
        if membership and (membership.is_administrator or membership.is_contributor or membership.is_moderator):
            return True
        
        return False
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
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='added_connections', 
                                on_delete=models.SET_NULL, null=True, blank=True)
    moderated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='moderated_connections', 
                                    on_delete=models.SET_NULL, null=True, blank=True)
    added_date = models.DateTimeField(auto_now_add=True)
    moderated_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('from_project', 'to_project', 'type')

    def __str__(self):
        return f"{self.from_project.name} -> {self.to_project.name} ({self.type})"


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ProjectPermissionGroup.choices, default='VIEWER')
    date_joined = models.DateTimeField(auto_now_add=True)
    is_moderator = models.BooleanField(default=False)
    is_administrator = models.BooleanField(default=False)
    is_owner = models.BooleanField(default=False)
    is_contributor = models.BooleanField(default=False)
    
    # New field for fine-grained permissions
    custom_permissions = models.JSONField(default=dict, blank=True,
        help_text="Custom permission overrides for this membership")

    class Meta:
        unique_together = ('user', 'project')
        permissions = [
            ("can_moderate_comments", "Can moderate comments"),
            ("can_approve_connections", "Can approve project connections"),
            ("can_edit_project", "Can edit project details"),
            ("can_add_members", "Can add members to project"),
            ("can_remove_members", "Can remove members from project"),
            ("can_view_analytics", "Can view project analytics"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.get_role_display()})"


def create_default_project_groups():
    """Create default permission groups for projects"""
    # Define the content types we need permissions for
    # The '_ct' suffix stands for 'content type' - these are Django ContentType objects
    # that identify which model a permission applies to in Django's permission system
    project_ct = ContentType.objects.get_for_model(Project)
    membership_ct = ContentType.objects.get_for_model(Membership)
    comment_ct = ContentType.objects.get_for_model('comment', 'Comment')
    report_ct = ContentType.objects.get_for_model('comment', 'CommentReport')
    
    # Define permissions for each role
    roles = {
        'Project Admin': {
            'permissions': [
                (project_ct, 'add_project'),
                (project_ct, 'change_project'),
                (project_ct, 'view_project'),
                (membership_ct, 'add_membership'),
                (membership_ct, 'change_membership'),
                (membership_ct, 'delete_membership'),
                (comment_ct, 'add_comment'),
                (comment_ct, 'change_comment'),
                (comment_ct, 'delete_comment'),
                (report_ct, 'change_commentreport'),
            ]
        },
        'Project Moderator': {
            'permissions': [
                (project_ct, 'view_project'),
                (comment_ct, 'add_comment'),
                (comment_ct, 'change_comment'),
                (comment_ct, 'delete_comment'),
                (report_ct, 'change_commentreport'),
            ]
        },
        'Project Contributor': {
            'permissions': [
                (project_ct, 'view_project'),
                (comment_ct, 'add_comment'),
                (comment_ct, 'change_own_comment'),
            ]
        },
        'Project Viewer': {
            'permissions': [
                (project_ct, 'view_project'),
                (comment_ct, 'add_comment'),
            ]
        }
    }
    
    # Create or update the groups with their permissions
    for group_name, group_data in roles.items():
        group, created = Group.objects.get_or_create(name=group_name)
        
        # Clear existing permissions
        group.permissions.clear()
        
        # Add permissions
        for content_type, codename in group_data['permissions']:
            try:
                perm = Permission.objects.get(content_type=content_type, codename=codename)
                group.permissions.add(perm)
            except Permission.DoesNotExist:
                print(f"Permission {codename} does not exist for {content_type}")