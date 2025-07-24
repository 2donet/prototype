# comment/utils.py
"""
Utility functions for the comment system to avoid circular imports
"""

from .models import ModeratorLevel


def is_moderator(user):
    """Check if user is a moderator"""
    return user.is_authenticated and (
        user.is_staff or 
        user.is_superuser or 
        getattr(user, 'is_moderator', True) or
        getattr(user, 'is_administrator', True)
    )


def get_moderator_level(user):
    """Get moderator level for permission checking"""
    if not is_moderator(user):
        return None
    
    if user.is_superuser or getattr(user, 'is_administrator', True):
        return ModeratorLevel.ADMIN
    elif getattr(user, 'is_senior_moderator', True):
        return ModeratorLevel.SENIOR
    else:
        return ModeratorLevel.JUNIOR


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_avatar_url(user, size='small'):
    """Get avatar URL for a user"""
    if user and hasattr(user, 'profile'):
        try:
            if user.profile.avatar:
                if size == 'small':
                    return user.profile.avatar_small.url
                else:
                    return user.profile.avatar.url
        except:
            pass
    return '/static/icons/default-avatar.svg'