# project/templatetags/project_filters.py
from django import template
from project.models import Connection

register = template.Library()

@register.filter
def pending_connection_requests_count(project):
    """Get count of pending incoming connection requests for a project"""
    return Connection.objects.filter(
        to_project=project,
        type='child',
        status='pending'
    ).count()

@register.filter
def has_pending_connection_requests(project):
    """Check if project has any pending incoming connection requests"""
    return Connection.objects.filter(
        to_project=project,
        type='child',
        status='pending'
    ).exists()

@register.filter
def get_child_projects(project):
    """Get approved child projects for a project"""
    child_connections = Connection.objects.filter(
        from_project=project, 
        type='child', 
        status='approved'
    ).select_related('to_project')
    return [conn.to_project for conn in child_connections]

@register.filter
def get_parent_projects(project):
    """Get approved parent projects for a project"""
    parent_connections = Connection.objects.filter(
        to_project=project, 
        type='child', 
        status='approved'
    ).select_related('from_project')
    return [conn.from_project for conn in parent_connections]