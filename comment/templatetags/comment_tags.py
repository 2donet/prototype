from django import template

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