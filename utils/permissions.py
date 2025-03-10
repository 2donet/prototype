from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib import messages
from project.models import Project, Membership


def user_has_project_permission(user, project, permission_type):
    """
    Check if a user has a specific permission for a project.
    
    Args:
        user: The user to check
        project: The project object or ID
        permission_type: String identifying the permission to check
            ('can_comment', 'can_moderate', 'can_edit', etc.)
    
    Returns:
        Boolean indicating if user has permission
    """
    if not user.is_authenticated:
        return False
        
    # Site-wide admin can do anything
    if user.is_superuser:
        return True
        
    # Get project instance if an ID was passed
    if isinstance(project, int):
        try:
            project = Project.objects.get(id=project)
        except Project.DoesNotExist:
            return False
            
    # Check project membership
    try:
        membership = Membership.objects.get(user=user, project=project)
    except Membership.DoesNotExist:
        # User not a member, check project visibility
        if permission_type == 'can_view' and project.visibility in ['public', 'logged_in']:
            return True
        return False
    
    # Check permission based on membership role
    if permission_type == 'can_admin':
        return membership.is_administrator
    elif permission_type == 'can_moderate':
        return membership.is_moderator or membership.is_administrator
    elif permission_type == 'can_contribute':
        return membership.is_contributor or membership.is_moderator or membership.is_administrator
    elif permission_type == 'can_comment':
        # All members can comment
        return True
    elif permission_type == 'can_view':
        # All members can view
        return True
        
    # Check for custom permissions
    if membership.custom_permissions and permission_type in membership.custom_permissions:
        return membership.custom_permissions[permission_type]
        
    # Default deny for unknown permission types
    return False


def requires_project_permission(permission_type, project_id_param='project_id'):
    """
    Decorator for views that checks if the user has the specified project permission.
    
    Args:
        permission_type: Type of permission required ('can_admin', 'can_moderate', etc.)
        project_id_param: The URL parameter name that contains the project ID
        
    Usage:
        @requires_project_permission('can_moderate')
        def my_view(request, project_id):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            project_id = kwargs.get(project_id_param)
            
            if not project_id:
                return HttpResponseForbidden("Project ID not provided")
                
            # Get the project
            project = get_object_or_404(Project, id=project_id)
            
            # Check permission
            if user_has_project_permission(request.user, project, permission_type):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "You don't have permission to perform this action.")
                return redirect('project:project', project_id=project_id)
                
        return _wrapped_view
    return decorator


def can_moderate_comment(user, comment):
    """
    Check if a user can moderate a specific comment.
    
    This is a helper function that determines the project context
    from the comment and checks appropriate permissions.
    """
    if not user.is_authenticated:
        return False
        
    # Site-wide admins and moderators can moderate any comment
    if user.is_superuser or user.is_staff:
        return True
        
    # For project comments, check project moderation permissions
    if comment.to_project:
        return user_has_project_permission(user, comment.to_project, 'can_moderate')
        
    # For task comments
    if comment.to_task and comment.to_task.to_project:
        return user_has_project_permission(user, comment.to_task.to_project, 'can_moderate')
        
    # For need comments
    if comment.to_need and comment.to_need.to_project:
        return user_has_project_permission(user, comment.to_need.to_project, 'can_moderate')
        
    # For comment replies, check the parent comment's context
    if comment.parent:
        return can_moderate_comment(user, comment.parent)
        
    # Default to False for any other case
    return False


def get_user_projects(user, role=None):
    """
    Get all projects a user is a member of, optionally filtered by role.
    
    Args:
        user: The user to get projects for
        role: Optional role to filter by (e.g., 'ADMIN', 'MODERATOR')
        
    Returns:
        QuerySet of Project objects
    """
    if not user.is_authenticated:
        return Project.objects.none()
        
    # Base query - all projects the user is a member of
    query = Project.objects.filter(membership__user=user)
    
    # Filter by role if specified
    if role:
        query = query.filter(membership__role=role)
        
    return query.distinct()


def get_user_moderation_projects(user):
    """Get all projects a user can moderate"""
    if user.is_superuser or user.is_staff:
        # Site-wide moderators can moderate all projects
        return Project.objects.all()
        
    # Get projects where user is moderator or admin
    return Project.objects.filter(
        membership__user=user,
        membership__is_moderator=True
    ).distinct()