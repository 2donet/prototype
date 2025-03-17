def notify_comment_reply(comment):
    """Notify a user when someone replies to their comment"""
    if comment.parent and comment.parent.user:
        # Create a notification record
        Notification.objects.create(
            user=comment.parent.user,
            content_type=ContentType.objects.get_for_model(Comment),
            object_id=comment.id,
            notification_type='REPLY',
            text=f"{comment.user.username if comment.user else 'Someone'} replied to your comment"
        )

def notify_comment_moderation(comment, action, moderator):
    """Notify a user when their comment is moderated"""
    if comment.user:
        Notification.objects.create(
            user=comment.user,
            notification_type='MODERATION',
            text=f"Your comment was {action} by a moderator"
        )