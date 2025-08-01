from django import template
from django.templatetags.static import static
from django.utils.safestring import mark_safe
from django.db import models
from comment.models import ModeratorLevel

register = template.Library()

@register.filter
def reaction_emoji(reaction_type):
    """Convert a reaction type to an emoji"""
    emoji_map = {
        'IDEA': '💡',
        'ISSUE': '⚠️',
        'QUESTION': '❔',
        'PLAN': '📋',
        'INFO': 'ℹ️'
    }
    return emoji_map.get(reaction_type, '💡')


@register.simple_tag
def user_avatar_url(user, size='small'):
    """
    Get the avatar URL for a user with fallback to default avatar
    
    Usage in templates:
    {% load comment_tags %}
    {% user_avatar_url comment.user 'small' %}
    {% user_avatar_url comment.user 'thumbnail' %}
    """
    if not user:
        return static('icons/default-avatar.svg')
    
    try:
        # Check if user has a profile
        if hasattr(user, 'profile') and user.profile:
            profile = user.profile
            
            # Check if profile has an avatar
            if hasattr(profile, 'avatar') and profile.avatar:
                if size == 'small' and hasattr(profile, 'avatar_small'):
                    return profile.avatar_small.url
                elif size == 'thumbnail' and hasattr(profile, 'avatar_thumbnail'):
                    return profile.avatar_thumbnail.url
                else:
                    # Fallback to original avatar
                    return profile.avatar.url
    except:
        # Any error in accessing avatar, use default
        pass
    
    return static('icons/default-avatar.svg')


@register.inclusion_tag('comment_avatar.html')
def comment_avatar(user, css_class='miniavatar circle'):
    """
    Render a comment avatar with proper fallback
    
    Usage in templates:
    {% load comment_tags %}
    {% comment_avatar comment.user %}
    {% comment_avatar comment.user 'custom-avatar-class' %}
    """
    return {
        'user': user,
        'avatar_url': user_avatar_url(user, 'small'),
        'css_class': css_class
    }


@register.simple_tag
def comment_avatar(user, size='small'):
    """Render user avatar for comments"""
    if user and hasattr(user, 'profile') and user.profile.avatar:
        if size == 'small':
            avatar_url = user.profile.avatar_small.url
        else:
            avatar_url = user.profile.avatar.url
    else:
        avatar_url = '/static/icons/default-avatar.svg'
    
    return mark_safe(f'<img src="{avatar_url}" alt="{user.username if user else "Anonymous"}" class="comment-avatar {size}">')


@register.filter
def moderator_level_badge(user):
    """Display moderator level badge"""
    if not user.is_authenticated:
        return ""
    
    if user.is_superuser:
        return mark_safe('<span class="badge red">Admin</span>')
    elif getattr(user, 'is_senior_moderator', False):
        return mark_safe('<span class="badge orange">Senior Mod</span>')
    elif getattr(user, 'is_moderator', False):
        return mark_safe('<span class="badge blue">Moderator</span>')
    
    return ""


@register.filter 
def can_moderate_comment(user, comment):
    """Check if user can moderate a specific comment"""
    return comment.can_moderate(user)


@register.inclusion_tag('comment_moderation_status.html')
def show_moderation_status(comment):
    """Show moderation status for a comment"""
    return {
        'comment': comment,
        'has_reports': comment.reports.exists(),
        'pending_reports': comment.reports.filter(status='PENDING').count(),
    }


# New template tags for changelog functionality

@register.filter
def has_change_history(comment):
    """Check if comment has any change history"""
    return hasattr(comment, 'change_log') and comment.change_log.exists()


@register.filter
def has_moderation_history(comment):
    """Check if comment has moderation history"""
    if hasattr(comment, 'has_moderation_history'):
        return comment.has_moderation_history()
    return False


@register.filter
def change_count(comment):
    """Get total number of changes for a comment"""
    if hasattr(comment, 'change_log'):
        return comment.change_log.count()
    return 0


@register.filter
def moderation_change_count(comment):
    """Get number of moderation changes for a comment"""
    if hasattr(comment, 'change_log'):
        from comment.models import ChangeType
        return comment.change_log.filter(
            change_type__in=[
                ChangeType.MODERATOR_EDIT,
                ChangeType.STATUS_CHANGE,
                ChangeType.CONTENT_REMOVAL,
                ChangeType.AUTHOR_REMOVAL,
                ChangeType.AUTHOR_AND_CONTENT_REMOVAL,
                ChangeType.THREAD_DELETION,
                ChangeType.BULK_THREAD_DELETION,
                ChangeType.APPROVAL,
                ChangeType.REJECTION,
                ChangeType.FLAGGED,
            ]
        ).count()
    return 0


@register.simple_tag
def get_original_content(comment):
    """Get the original content of a comment before any changes"""
    if hasattr(comment, 'get_original_content'):
        return comment.get_original_content()
    return comment.content


@register.filter
def change_type_icon(change_type):
    """Get icon for different change types"""
    icons = {
        'USER_EDIT': '✏️',
        'MODERATOR_EDIT': '🛠️',
        'STATUS_CHANGE': '🔄',
        'CONTENT_REMOVAL': '🗑️',
        'AUTHOR_REMOVAL': '👤❌',
        'AUTHOR_AND_CONTENT_REMOVAL': '🚫',
        'THREAD_DELETION': '🗑️🧵',
        'BULK_THREAD_DELETION': '🗑️📁',
        'APPROVAL': '✅',
        'REJECTION': '❌',
        'FLAGGED': '🚩',
    }
    return icons.get(change_type, '📝')


@register.filter
def change_type_color(change_type):
    """Get CSS class for different change types"""
    colors = {
        'USER_EDIT': 'information',
        'MODERATOR_EDIT': 'warning',
        'STATUS_CHANGE': 'status-purple',
        'CONTENT_REMOVAL': 'danger',
        'AUTHOR_REMOVAL': 'risk',
        'AUTHOR_AND_CONTENT_REMOVAL': 'status-pink',
        'THREAD_DELETION': 'bg-color',
        'BULK_THREAD_DELETION': 'status-dark',
        'APPROVAL': 'confirm',
        'REJECTION': 'danger',
        'FLAGGED': 'warning',
    }
    return colors.get(change_type, 'information')


@register.inclusion_tag('changelog_summary.html')
def changelog_summary(comment, max_entries=3):
    """Display a summary of recent changes for a comment"""
    if not hasattr(comment, 'change_log'):
        return {'changes': [], 'comment': comment}
    
    recent_changes = comment.change_log.select_related('changed_by')[:max_entries]
    return {
        'changes': recent_changes,
        'comment': comment,
        'total_changes': comment.change_log.count(),
        'max_entries': max_entries
    }


@register.filter
def is_user_edit(changelog_entry):
    """Check if this is a user edit (not moderator action)"""
    return changelog_entry.change_type == 'USER_EDIT'


@register.filter
def is_moderator_action(changelog_entry):
    """Check if this is a moderator action"""
    moderator_actions = [
        'MODERATOR_EDIT', 'STATUS_CHANGE', 'CONTENT_REMOVAL',
        'AUTHOR_REMOVAL', 'AUTHOR_AND_CONTENT_REMOVAL',
        'THREAD_DELETION', 'BULK_THREAD_DELETION',
        'APPROVAL', 'REJECTION', 'FLAGGED'
    ]
    return changelog_entry.change_type in moderator_actions


@register.filter
def get_edit_type_display(changelog_entry):
    """Get a user-friendly display for edit types"""
    if changelog_entry.change_type == 'USER_EDIT':
        return "User Edit"
    elif changelog_entry.change_type == 'MODERATOR_EDIT':
        return "Moderator Edit"
    else:
        return changelog_entry.get_change_type_display()


@register.filter
def was_edited_by_moderator(comment):
    """Check if comment was ever edited by a moderator"""
    try:
        return comment.change_log.filter(change_type='MODERATOR_EDIT').exists()
    except:
        return False


@register.filter
def was_edited_by_user(comment):
    """Check if comment was ever edited by the user themselves"""
    try:
        return comment.change_log.filter(change_type='USER_EDIT').exists()
    except:
        return False


@register.inclusion_tag('changelog_summary.html')
def changelog_summary(comment, max_entries=3):
    """Display a summary of recent changes for a comment"""
    if not hasattr(comment, 'change_log'):
        return {'changes': [], 'comment': comment}
    
    recent_changes = comment.change_log.select_related('changed_by')[:max_entries]
    return {
        'changes': recent_changes,
        'comment': comment,
        'total_changes': comment.change_log.count(),
        'max_entries': max_entries
    }


@register.filter
def can_view_comment_history(user, comment):
    """Check if user can view comment history"""
    if not user.is_authenticated:
        return False
    
    # Global admins can see everything
    if user.is_superuser or user.is_staff:
        return True
    
    # Project moderators can see moderation history
    if hasattr(comment, 'can_moderate') and comment.can_moderate(user):
        return True
    
    return False


@register.filter
def can_view_all_changes(user, comment):
    """Check if user can view all changes (including user edits)"""
    if not user.is_authenticated:
        return False
    
    # Only global admins can see all changes
    return user.is_superuser or user.is_staff


@register.filter
def is_bulk_operation(changelog_entry):
    """Check if changelog entry is part of a bulk operation"""
    return bool(changelog_entry.bulk_operation_id)


@register.filter
def format_change_reason(reason):
    """Format change reason for display"""
    if not reason:
        return "No reason provided"
    
    # Truncate very long reasons
    if len(reason) > 100:
        return reason[:97] + "..."
    
    return reason


@register.simple_tag
def get_status_badge_class(status):
    """Get CSS class for status badges"""
    status_classes = {
        'PENDING': 'status-pending',
        'APPROVED': 'status-approved',
        'REJECTED': 'status-rejected',
        'FLAGGED': 'status-flagged',
        'CONTENT_REMOVED': 'status-content_removed',
        'AUTHOR_REMOVED': 'status-author_removed',
        'AUTHOR_AND_CONTENT_REMOVED': 'status-author_and_content_removed',
        'THREAD_DELETED': 'status-thread_deleted',
        'REPLY_TO_DELETED': 'status-reply_to_deleted',
    }
    return status_classes.get(status, 'status-default')

@register.filter
def nested_reply_count(comment, user=None):
    """
    Get the total count of nested replies for a comment
    
    Usage: {{ comment|nested_reply_count:user }}
    """
    from comment.models import CommentStatus
    
    if not comment:
        return 0
    
    # Determine which statuses to include based on user permissions
    if user and user.is_authenticated and hasattr(comment, 'can_moderate') and comment.can_moderate(user):
        # Moderators see more statuses
        include_statuses = [
            CommentStatus.APPROVED,
            CommentStatus.PENDING,
            CommentStatus.FLAGGED,
            CommentStatus.REJECTED,
            CommentStatus.CONTENT_REMOVED,
            CommentStatus.AUTHOR_REMOVED,
            CommentStatus.AUTHOR_AND_CONTENT_REMOVED,
        ]
    else:
        # Regular users only see approved
        include_statuses = [CommentStatus.APPROVED]
    
    # Use the new method if it exists, otherwise fallback to the old field
    if hasattr(comment, 'get_total_nested_replies'):
        return comment.get_total_nested_replies(include_statuses)
    else:
        return comment.total_replies or 0

@register.filter  
def total_nested_replies_for_project(project, user=None):
    """
    Get total nested replies for a project
    
    Usage: {{ project|total_nested_replies_for_project:user }}
    """
    if hasattr(project, 'get_comment_statistics'):
        stats = project.get_comment_statistics(user)
        return stats['total_replies']
    else:
        # Fallback to old method
        from comment.models import Comment
        return Comment.objects.filter(to_project=project).aggregate(
            total=models.Sum('total_replies')
        )['total'] or 0