from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class Comment(models.Model):
    content = models.TextField("description")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )  # Self-referential ForeignKey for replies
    user = models.ForeignKey("user.User", on_delete=models.CASCADE, db_index=True)
    to_comment = models.ForeignKey("self", blank=True, null=True, on_delete=models.CASCADE, related_name="related_comments", db_index=True)
    to_project = models.ForeignKey("project.Project", blank=True, null=True, on_delete=models.CASCADE, related_name="comments", db_index=True)
    to_task = models.ForeignKey("task.Task", blank=True, null=True, on_delete=models.CASCADE, related_name="comments", db_index=True)
    to_need = models.ForeignKey("need.Need", blank=True, null=True, on_delete=models.CASCADE, related_name="comments", db_index=True)
    to_report = models.ForeignKey("moderation.Report", blank=True, null=True, on_delete=models.CASCADE, related_name="comments", db_index=True)
    to_membership = models.ForeignKey("user.Membership", blank=True, null=True, on_delete=models.CASCADE, related_name="comments", db_index=True)
    to_decision = models.ForeignKey("decisions.Decision", blank=True, null=True, on_delete=models.CASCADE, related_name="comments", db_index=True)

    def __str__(self):
        return self.content[:20]

    @staticmethod
    def update_reply_count(comment):
        """
        Recursively update the total_replies count of all parent comments.
        """
        while comment:
            comment.total_replies = comment.replies.count()
            comment.save()
            comment = comment.parent

# Signals to update `total_replies` automatically
@receiver(post_save, sender=Comment)
def update_replies_on_save(sender, instance, **kwargs):
    if instance.parent:
        Comment.update_reply_count(instance.parent)

@receiver(post_delete, sender=Comment)
def update_replies_on_delete(sender, instance, **kwargs):
    if instance.parent:
        Comment.update_reply_count(instance.parent)



    # def __str__(self):
    #     return self.name

# Validation: Consider adding validation to ensure a comment is associated with at least one of the target models (to_project, to_task, etc.).
#     For example, you can override the save method or use a custom validator.
# def save(self, *args, **kwargs):
#     if not any([self.to_project, self.to_task, self.to_need, self.to_report, self.to_membership]):
#         raise ValueError("A comment must be associated with at least one target.")
#     super().save(*args, **kwargs)



