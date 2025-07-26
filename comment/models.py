from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone

from django.db.models import Sum, Count, Q
from django.utils.translation import gettext_lazy as _



class CommentStatus(models.TextChoices):
    """Status options for comments"""
    PENDING = 'PENDING', 'Pending Approval'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    FLAGGED = 'FLAGGED', 'Flagged for Review'
    # New moderation statuses
    CONTENT_REMOVED = 'CONTENT_REMOVED', 'Content Removed by Moderation'
    AUTHOR_REMOVED = 'AUTHOR_REMOVED', 'Author Hidden by Moderation'
    AUTHOR_AND_CONTENT_REMOVED = 'AUTHOR_AND_CONTENT_REMOVED', 'Author and Content Removed'
    THREAD_DELETED = 'THREAD_DELETED', 'Thread Deleted by Moderation'
    REPLY_TO_DELETED = 'REPLY_TO_DELETED', 'Reply to Deleted Comment'


class Comment(models.Model):
    content = models.TextField("description")
    score = models.IntegerField(default=0)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, db_index=True,
        related_name="comments"
    )
    to_project = models.ForeignKey(
        "project.Project", null=True, blank=True, on_delete=models.CASCADE, related_name="comments"
    )
    total_replies = models.PositiveIntegerField(default=0)

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

    status = models.CharField(
        max_length=26,
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

    author_name = models.CharField(max_length=50, blank=True, null=True,
        help_text="Optional name for anonymous users")
    author_email = models.EmailField(blank=True, null=True,
        help_text="Optional email for anonymous users")

    is_edited = models.BooleanField(default=False)
    edit_history = models.JSONField(default=list, blank=True,
        help_text="History of edits to this comment")

    def __str__(self):
        return f"{self.content[:20]} by {self.user.username if self.user else self.author_name or 'Anonymous'}"

    def update_reply_count(self):
        comment = self
        while comment:
            comment.total_replies = comment.replies.filter(status=CommentStatus.APPROVED).count()
            comment.save(update_fields=["total_replies"])
            comment = comment.parent

    def approve(self, moderator=None):
        self.status = CommentStatus.APPROVED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        self.save()

    def reject(self, moderator=None, note=None):
        self.status = CommentStatus.REJECTED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        if note:
            self.moderation_note = note
        self.save()

    def flag(self, moderator=None, note=None):
        self.status = CommentStatus.FLAGGED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        if note:
            self.moderation_note = note
        self.save()

    def edit(self, new_content, editor=None):
        history_entry = {
            'content': self.content,
            'edited_at': timezone.now().isoformat(),
            'edited_by': editor.username if editor else None
        }
        if not self.is_edited:
            self.is_edited = True
            self.edit_history = [history_entry]
        else:
            self.edit_history.append(history_entry)
        self.content = new_content
        self.save()

    def can_moderate(self, user):
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        if self.to_project:
            return self.to_project.user_can_moderate_comments(user)
        if self.to_task and self.to_task.to_project:
            return self.to_task.to_project.user_can_moderate_comments(user)
        if self.to_need and self.to_need.to_project:
            return self.to_need.to_project.user_can_moderate_comments(user)
        return False

    def soft_delete_thread(self, moderator=None, reason=None):
        self.status = CommentStatus.THREAD_DELETED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        if reason:
            self.moderation_note = reason
        self.save()
        self.mark_replies_deleted(moderator)

    def mark_replies_deleted(self, moderator=None):
        for reply in self.replies.all():
            if reply.status == CommentStatus.APPROVED:
                reply.status = CommentStatus.REPLY_TO_DELETED
                reply.moderated_by = moderator
                reply.moderated_at = timezone.now()
                reply.save()
                reply.mark_replies_deleted(moderator)
        if self.parent:
            self.parent.update_reply_count()

    def can_edit(self, user):
        if not user.is_authenticated:
            return False
        if self.user == user:
            return True
        return self.can_moderate(user)

    def remove_content_only(self, moderator=None, reason=None):
        self.content = "[Content removed by moderation]"
        self.status = CommentStatus.CONTENT_REMOVED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        if reason:
            self.moderation_note = reason
        self.save()

    def remove_author_only(self, moderator=None, reason=None):
        self.status = CommentStatus.AUTHOR_REMOVED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        if reason:
            self.moderation_note = reason
        self.save()

    def remove_author_and_content(self, moderator=None, reason=None):
        self.content = "[Content removed by moderation]"
        self.status = CommentStatus.AUTHOR_AND_CONTENT_REMOVED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        if reason:
            self.moderation_note = reason
        self.save()

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





class VoteType(models.TextChoices):
    """Type of votes a user can cast on a comment"""
    UPVOTE = 'UPVOTE', _('Upvote')
    DOWNVOTE = 'DOWNVOTE', _('Downvote')




class CommentVote(models.Model):
    """Model to track votes on comments"""
    comment = models.ForeignKey(
        'comment.Comment',
        on_delete=models.CASCADE,
        related_name='votes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comment_votes'
    )
    vote_type = models.CharField(
        max_length=10,
        choices=VoteType.choices,
        default=VoteType.UPVOTE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('comment', 'user')
        verbose_name = _('Comment Vote')
        verbose_name_plural = _('Comment Votes')
        indexes = [
            models.Index(fields=['comment', 'vote_type']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.username}'s {self.get_vote_type_display()} on comment {self.comment.id}"
    
    def save(self, *args, **kwargs):
        if self.pk:
            old_vote = CommentVote.objects.get(pk=self.pk)
            vote_changed = old_vote.vote_type != self.vote_type
        else:
            vote_changed = True
        
        super().save(*args, **kwargs)
        
        if vote_changed:
            self.update_comment_score()
        
    def delete(self, *args, **kwargs):
        comment = self.comment  # Store reference before deletion
        super().delete(*args, **kwargs)
        # Update score after deletion
        self.update_comment_score(comment)
        
    def update_comment_score(self, comment=None):
        """Update the score field on the associated comment"""
        comment = comment or self.comment
        
        # Count upvotes and downvotes
        upvotes = comment.votes.filter(vote_type=VoteType.UPVOTE).count()
        downvotes = comment.votes.filter(vote_type=VoteType.DOWNVOTE).count()
        
        # Update the score
        comment.score = upvotes - downvotes
        comment.save(update_fields=['score'])

class ModeratorLevel(models.TextChoices):
    """Different levels of moderators with different permissions"""
    JUNIOR = 'JUNIOR', 'Junior Moderator'
    SENIOR = 'SENIOR', 'Senior Moderator'
    ADMIN = 'ADMIN', 'Admin Moderator'


class ModerationDecision(models.TextChoices):
    """Types of moderation decisions"""
    APPROVE = 'APPROVE', 'Approve Comment (Dismiss Reports)'
    HIDE = 'HIDE', 'Hide Comment'
    REMOVE = 'REMOVE', 'Remove Comment'
    EDIT = 'EDIT', 'Edit Comment Content'
    WARN_USER = 'WARN_USER', 'Warn User'
    SUSPEND_USER = 'SUSPEND_USER', 'Suspend User'
    BAN_USER = 'BAN_USER', 'Ban User'
    FALSE_REPORT = 'FALSE_REPORT', 'Mark as False Report'
    # New moderation decisions
    REMOVE_CONTENT_ONLY = 'REMOVE_CONTENT_ONLY', 'Remove Content Only'
    REMOVE_AUTHOR_ONLY = 'REMOVE_AUTHOR_ONLY', 'Remove Author Only'
    REMOVE_AUTHOR_AND_CONTENT = 'REMOVE_AUTHOR_AND_CONTENT', 'Remove Author and Content'
    DELETE_THREAD = 'DELETE_THREAD', 'Delete Entire Thread'

class DecisionScope(models.TextChoices):
    """Scope of moderation decision application"""
    ALL_REPORTS = 'ALL_REPORTS', 'Apply to All Reports'
    REPORT_TYPE = 'REPORT_TYPE', 'Apply to Specific Report Type'
    SINGLE_REPORT = 'SINGLE_REPORT', 'Apply to Single Report Only'


class ModerationAction(models.Model):
    """Model to track all moderation actions for audit trail"""
    
    # Basic info
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='moderation_actions'
    )
    comment = models.ForeignKey(
        'Comment',
        on_delete=models.CASCADE,
        related_name='moderation_actions'
    )
    
    # Decision details
    decision = models.CharField(
        max_length=25,
        choices=ModerationDecision.choices
    )
    decision_scope = models.CharField(
        max_length=25,
        choices=DecisionScope.choices,
        default=DecisionScope.ALL_REPORTS
    )
    target_report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        null=True,
        blank=True,
        help_text="Only used when scope is REPORT_TYPE"
    )
    target_report = models.ForeignKey(
        'CommentReport',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Only used when scope is SINGLE_REPORT"
    )
    
    # Action details
    reason = models.TextField(help_text="Moderator's reason for this decision")
    notify_reporters = models.BooleanField(default=True)
    escalate_to_platform = models.BooleanField(
        default=False,
        help_text="Report to platform-wide moderation"
    )
    
    # Content changes (for EDIT decisions)
    original_content = models.TextField(blank=True, null=True)
    new_content = models.TextField(blank=True, null=True)
    
    # User impact (for user-level decisions)
    affected_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='moderation_impacts'
    )
    suspension_until = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Project context
    project = models.ForeignKey(
        "project.Project",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="moderation_actions"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['decision']),
            models.Index(fields=['created_at']),
            models.Index(fields=['moderator']),
        ]
    
    def __str__(self):
        return f"{self.get_decision_display()} by {self.moderator.username} on comment {self.comment.id}"
    

    def apply_decision(self):
        """Apply the moderation decision to the comment and related objects"""
        
        # Apply comment-level changes
        if self.decision == ModerationDecision.APPROVE:
            self.comment.status = CommentStatus.APPROVED
            self.comment.moderated_by = self.moderator
            self.comment.moderated_at = timezone.now()
            
        elif self.decision == ModerationDecision.HIDE:
            self.comment.status = CommentStatus.FLAGGED
            self.comment.moderated_by = self.moderator
            self.comment.moderated_at = timezone.now()
            
        elif self.decision == ModerationDecision.REMOVE:
            self.comment.status = CommentStatus.REJECTED
            self.comment.moderated_by = self.moderator
            self.comment.moderated_at = timezone.now()
            
        elif self.decision == ModerationDecision.EDIT:
            if self.new_content:
                self.original_content = self.comment.content
                self.comment.content = self.new_content
                self.comment.is_edited = True
                
        # New moderation decisions
        elif self.decision == ModerationDecision.REMOVE_CONTENT_ONLY:
            self.comment.remove_content_only(moderator=self.moderator, reason=self.reason)
            
        elif self.decision == ModerationDecision.REMOVE_AUTHOR_ONLY:
            self.comment.remove_author_only(moderator=self.moderator, reason=self.reason)
            
        elif self.decision == ModerationDecision.REMOVE_AUTHOR_AND_CONTENT:
            self.comment.remove_author_and_content(moderator=self.moderator, reason=self.reason)
            
        elif self.decision == ModerationDecision.DELETE_THREAD:
            self.comment.soft_delete_thread(moderator=self.moderator, reason=self.reason)
            
        # Only save if it's not a thread deletion (that method handles its own saving)
        if self.decision != ModerationDecision.DELETE_THREAD:
            self.comment.save()
        
        # Apply to reports based on scope
        reports_to_resolve = []
        
        if self.decision_scope == DecisionScope.ALL_REPORTS:
            reports_to_resolve = self.comment.reports.filter(
                status__in=[ReportStatus.PENDING, ReportStatus.REVIEWED]
            )
        elif self.decision_scope == DecisionScope.REPORT_TYPE:
            reports_to_resolve = self.comment.reports.filter(
                status__in=[ReportStatus.PENDING, ReportStatus.REVIEWED],
                report_type=self.target_report_type
            )
        elif self.decision_scope == DecisionScope.SINGLE_REPORT:
            if self.target_report:
                reports_to_resolve = [self.target_report]
        
        # Update report statuses
        for report in reports_to_resolve:
            if self.decision == ModerationDecision.FALSE_REPORT:
                report.status = ReportStatus.REJECTED
            else:
                report.status = ReportStatus.RESOLVED
            report.reviewed_by = self.moderator
            report.moderator_notes = f"Resolved via moderation action: {self.get_decision_display()}"
            report.save()
        
        # Handle user-level decisions
        if self.decision in [ModerationDecision.WARN_USER, ModerationDecision.SUSPEND_USER, ModerationDecision.BAN_USER]:
            self.affected_user = self.comment.user
            # User impact will be implemented later as requested
        
        # Notify reporters if requested
        if self.notify_reporters:
            self.notify_reporters_func()
    def notify_reporters_func(self):
        """Notify reporters about the moderation decision"""
        # Get relevant reports based on scope
        if self.decision_scope == DecisionScope.ALL_REPORTS:
            reports = self.comment.reports.all()
        elif self.decision_scope == DecisionScope.REPORT_TYPE:
            reports = self.comment.reports.filter(report_type=self.target_report_type)
        elif self.decision_scope == DecisionScope.SINGLE_REPORT:
            reports = [self.target_report] if self.target_report else []
        
        for report in reports:
            if report.reportee:
                # For now, just print as requested
                print(f"Report by {report.reportee.username} of comment '{self.comment.content[:50]}...' resolved as {self.get_decision_display()}")
                
                # TODO: Later implement actual notification system
                # This could be email, in-app notification, etc.


class CommentReportGroup(models.Model):
    """Virtual model to represent grouped reports for the same comment"""
    comment = models.OneToOneField(
        'Comment',
        on_delete=models.CASCADE,
        related_name='report_group'
    )
    total_reports = models.PositiveIntegerField(default=0)
    report_types_summary = models.JSONField(default=dict)  # {"SPAM": 3, "HARASSMENT": 2}
    first_reported_at = models.DateTimeField()
    last_reported_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING
    )
    
    class Meta:
        ordering = ['-last_reported_at']
    
    @classmethod
    def update_for_comment(cls, comment):
        """Update or create report group for a comment"""
        reports = comment.reports.all()
        
        if not reports.exists():
            # Delete group if no reports
            cls.objects.filter(comment=comment).delete()
            return None
        
        # Calculate summary
        report_summary = {}
        for report_type, _ in ReportType.choices:
            count = reports.filter(report_type=report_type).count()
            if count > 0:
                report_summary[report_type] = count
        
        # Determine overall status
        if reports.filter(status=ReportStatus.PENDING).exists():
            group_status = ReportStatus.PENDING
        elif reports.filter(status=ReportStatus.REVIEWED).exists():
            group_status = ReportStatus.REVIEWED
        else:
            group_status = ReportStatus.RESOLVED
        
        group, created = cls.objects.update_or_create(
            comment=comment,
            defaults={
                'total_reports': reports.count(),
                'report_types_summary': report_summary,
                'first_reported_at': reports.order_by('created_at').first().created_at,
                'last_reported_at': reports.order_by('-created_at').first().created_at,
                'status': group_status,
            }
        )
        return group
    
    def get_report_types_display(self):
        """Get human-readable report types summary"""
        display_parts = []
        for report_type, count in self.report_types_summary.items():
            type_display = dict(ReportType.choices)[report_type]
            display_parts.append(f"{count} {type_display}")
        return ", ".join(display_parts)
    
    def __str__(self):
        return f"{self.total_reports} reports on comment {self.comment.id}"
    

# Update CommentReport model with signals
@receiver(post_save, sender=CommentReport)
def update_report_group_on_save(sender, instance, **kwargs):
    CommentReportGroup.update_for_comment(instance.comment)


@receiver(post_delete, sender=CommentReport)
def update_report_group_on_delete(sender, instance, **kwargs):
    CommentReportGroup.update_for_comment(instance.comment)