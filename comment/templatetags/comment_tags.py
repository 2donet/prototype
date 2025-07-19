from django import template


from django.templatetags.static import static


register = template.Library()

@register.filter
def reaction_emoji(reaction_type):
    """Convert a reaction type to an emoji"""
    emoji_map = {
        'LIKE': '👍',
        'LOVE': '❤️',
        'LAUGH': '😂',
        'INSIGHTFUL': '💡',
        'CONFUSED': '😕',
        'SAD': '😢',
        'THANKS': '🙏'
    }
    return emoji_map.get(reaction_type, '👍')



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