from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings


class Comment(models.Model):
    content = models.TextField("description")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )  # Self-referential ForeignKey for replies
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_index=True
    )  # Allow null for anonymous users
    to_project = models.ForeignKey(
        "project.Project", null=True, blank=True, on_delete=models.CASCADE, related_name="comments"
    )
    total_replies = models.PositiveIntegerField(default=0)  # Cache for replies count

    to_comment = models.ForeignKey("self", blank=True, null=True, on_delete=models.CASCADE,
                                   related_name="related_comments", db_index=True)
    to_task = models.ForeignKey("task.Task", blank=True, null=True, on_delete=models.CASCADE, related_name="comments",
                                db_index=True)
    to_need = models.ForeignKey("need.Need", blank=True, null=True, on_delete=models.CASCADE, related_name="comments",
                                db_index=True)
    to_report = models.ForeignKey("moderation.Report", blank=True, null=True, on_delete=models.CASCADE,
                                  related_name="comments", db_index=True)
    to_membership = models.ForeignKey("user.Membership", blank=True, null=True, on_delete=models.CASCADE,
                                      related_name="comments", db_index=True)
    to_decision = models.ForeignKey("decisions.Decision", blank=True, null=True, on_delete=models.CASCADE,
                                    related_name="comments", db_index=True)

    def __str__(self):
        return f"{self.content[:20]} by {self.user.username if self.user else 'Anonymous'}"

    def update_reply_count(self):
        """
        Recursively update the total_replies count for parent comments.
        """
        comment = self
        while comment:
            comment.total_replies = comment.replies.count()
            comment.save(update_fields=["total_replies"])
            comment = comment.parent


# Signals to update `total_replies` automatically
@receiver(post_save, sender=Comment)
def update_replies_on_save(sender, instance, created, **kwargs):
    if created and instance.parent:
        instance.parent.update_reply_count()


@receiver(post_delete, sender=Comment)
def update_replies_on_delete(sender, instance, **kwargs):
    if instance.parent:
        instance.parent.update_reply_count()