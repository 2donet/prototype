from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone


class CommentStatus(models.TextChoices):
    """Status options for comments"""
    PENDING = 'PENDING', 'Pending Approval'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    FLAGGED = 'FLAGGED', 'Flagged for Review'


class Comment(models.Model):
    content = models.TextField("description")
    score = models.IntegerField(default=0)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )  # Self-referential ForeignKey for replies
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_index=True,
        related_name="comments"
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
                                    
    # New fields for moderation
    status = models.CharField(
        max_length=20, 
        choices=CommentStatus.choices,
        default=CommentStatus.APPROVED,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name="moderated_comments"
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderation_note = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # For anonymous users
    author_name = models.CharField(max_length=50, blank=True, null=True, 
        help_text="Optional name for anonymous users")
    author_email = models.EmailField(blank=True, null=True,
        help_text="Optional email for anonymous users")
        
    # Tracking edits
    is_edited = models.BooleanField(default=False)
    edit_history = models.JSONField(default=list, blank=True,
        help_text="History of edits to this comment")

    def __str__(self):
        return f"{self.content[:20]} by {self.user.username if self.user else self.author_name or 'Anonymous'}"

    def update_reply_count(self):
        """
        Recursively update the total_replies count for parent comments.
        """
        comment = self
        while comment:
            # Only count approved replies
            comment.total_replies = comment.replies.filter(status=CommentStatus.APPROVED).count()
            comment.save(update_fields=["total_replies"])
            comment = comment.parent
            
    def approve(self, moderator=None):
        """Approve a comment"""
        self.status = CommentStatus.APPROVED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        self.save()
        
    def reject(self, moderator=None, note=None):
        """Reject a comment"""
        self.status = CommentStatus.REJECTED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        if note:
            self.moderation_note = note
        self.save()
        
    def flag(self, moderator=None, note=None):
        """Flag a comment for further review"""
        self.status = CommentStatus.FLAGGED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        if note:
            self.moderation_note = note
        self.save()
    
    def edit(self, new_content, editor=None):
        """Edit a comment, preserving history"""
        # Store the current version in history
        history_entry = {
            'content': self.content,
            'edited_at': timezone.now().isoformat(),
            'edited_by': editor.username if editor else None
        }
        
        # Update history
        if not self.is_edited:
            self.is_edited = True
            self.edit_history = [history_entry]
        else:
            self.edit_history.append(history_entry)
            
        # Update content
        self.content = new_content
        self.save()
        
    def can_moderate(self, user):
        """Check if user can moderate this comment"""
        if not user.is_authenticated:
            return False
            
        # Global moderators
        if user.is_superuser or user.is_staff:
            return True
            
        # Project moderators
        if self.to_project:
            return self.to_project.user_can_moderate_comments(user)
            
        # Task moderators
        if self.to_task and self.to_task.to_project:
            return self.to_task.to_project.user_can_moderate_comments(user)
            
        # Need moderators
        if self.to_need and self.to_need.to_project:
            return self.to_need.to_project.user_can_moderate_comments(user)
            
        return False
        
    def can_edit(self, user):
        """Check if user can edit this comment"""
        if not user.is_authenticated:
            return False
            
        # Comment owner can edit (if authenticated)
        if self.user == user:
            return True
            
        # Moderators can edit
        return self.can_moderate(user)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]


# Signals to update `total_replies` automatically
@receiver(post_save, sender=Comment)
def update_replies_on_save(sender, instance, created, **kwargs):
    if created and instance.parent and instance.status == CommentStatus.APPROVED:
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
    
    # Add project reference for easier permission checks
    project = models.ForeignKey(
        "project.Project", 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        related_name="comment_reports"
    )
    
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
            
        # Set the project for easier permission checks
        if not self.project:
            if self.comment.to_project:
                self.project = self.comment.to_project
            elif self.comment.to_task and self.comment.to_task.to_project:
                self.project = self.comment.to_task.to_project
            elif self.comment.to_need and self.comment.to_need.to_project:
                self.project = self.comment.to_need.to_project
                
        super().save(*args, **kwargs)