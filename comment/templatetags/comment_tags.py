from django import template


from django.templatetags.static import static

from django.utils.safestring import mark_safe
from comment.models import ModeratorLevel

register = template.Library()


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
