from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings


class Comment(models.Model):
    content = models.TextField("description")
    score = models.IntegerField(default=0)
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


class ReportType(models.TextChoices):
    """Types of reports that can be filed against comments"""
    SPAM = 'SPAM', 'Spam or Excessive Self-Promotion'
    SCAM = 'SCAM', 'Scam or Fraudulent Content'
    THEFT = 'THEFT', 'Intellectual Property Theft'
    HARASSMENT = 'HARASSMENT', 'Harassment or Bullying'
    HATE_SPEECH = 'HATE_SPEECH', 'Hate Speech'
    MISINFORMATION = 'MISINFORMATION', 'Misinformation'
    OTHER = 'OTHER', 'Other'


class ReportStatus(models.TextChoices):
    """Status of comment reports"""
    PENDING = 'PENDING', 'Pending Review'
    REVIEWED = 'REVIEWED', 'Reviewed'
    REJECTED = 'REJECTED', 'Rejected'
    RESOLVED = 'RESOLVED', 'Resolved'


class CommentReport(models.Model):
    """Model for tracking reports against comments"""
    # User relations
    reportee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='filed_reports',
        help_text='User who filed the report'
    )
    reported = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reports_against',
        help_text='User whose comment was reported'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_reports',
        help_text='Moderator who reviewed the report'
    )
    
    # Report details
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='reports',
        help_text='The comment being reported'
    )
    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        default=ReportType.OTHER,
        help_text='Type of violation being reported'
    )
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        help_text='Current status of the report'
    )
    description = models.TextField(
        blank=True,
        help_text='Additional context provided by the reporter'
    )
    moderator_notes = models.TextField(
        blank=True,
        help_text='Notes from the moderator reviewing the report'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['report_type']),
        ]
    
    def __str__(self):
        reporter = self.reportee.username if self.reportee else "Anonymous"
        return f"{self.get_report_type_display()} report by {reporter} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # When creating a report, automatically set the reported user if the comment has a user
        if not self.pk and self.comment and self.comment.user and not self.reported:
            self.reported = self.comment.user
        super().save(*args, **kwargs)