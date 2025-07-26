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