from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Q


class ConversationManager(models.Manager):
    def get_or_create_conversation(self, user1, user2):
        """Get or create a conversation between two users"""
        conversation = self.filter(
            participants=user1
        ).filter(
            participants=user2
        ).filter(
            conversation_type='direct'
        ).first()
        
        if not conversation:
            conversation = self.create(conversation_type='direct')
            conversation.participants.add(user1, user2)
        
        return conversation
    
    def get_or_create_submission_conversation(self, admin_user, submitter, submission):
        """
        Get or create a submission-related conversation - one conversation per submission.
        This method now handles both admin-initiated and submitter-initiated conversations.
        """
        # Find existing conversation for this submission
        conversation = self.filter(
            conversation_type='submission',
            submission=submission
        ).first()
        
        if not conversation:
            # Create new conversation for this submission
            conversation = self.create(
                conversation_type='submission',
                submission=submission,
                created_by=admin_user  # Track who created the conversation
            )
            # Add both the admin and submitter as participants
            conversation.participants.add(admin_user, submitter)
            
            # Create ConversationParticipant records with proper joined_at timestamps
            ConversationParticipant.objects.get_or_create(
                conversation=conversation,
                user=admin_user,
                defaults={'joined_at': timezone.now()}
            )
            ConversationParticipant.objects.get_or_create(
                conversation=conversation,
                user=submitter,
                defaults={'joined_at': timezone.now()}
            )
        else:
            # Add admin to existing conversation if not already a participant
            if not conversation.participants.filter(id=admin_user.id).exists():
                conversation.participants.add(admin_user)
                # Create ConversationParticipant record
                ConversationParticipant.objects.get_or_create(
                    conversation=conversation,
                    user=admin_user,
                    defaults={'joined_at': timezone.now()}
                )
            
            # Ensure submitter is also a participant (should already be, but just in case)
            if not conversation.participants.filter(id=submitter.id).exists():
                conversation.participants.add(submitter)
                ConversationParticipant.objects.get_or_create(
                    conversation=conversation,
                    user=submitter,
                    defaults={'joined_at': timezone.now()}
                )
        
        return conversation
    
    def get_user_conversations(self, user):
        """Get all conversations for a user, ordered by last message"""
        return self.filter(
            participants=user
        ).prefetch_related(
            'participants', 'messages'
        ).annotate(
            last_message_time=models.Max('messages__timestamp')
        ).order_by('-last_message_time')


class Conversation(models.Model):
    CONVERSATION_TYPES = [
        ('direct', 'Direct Message'),
        ('thread', 'Thread Discussion'),  # For future use
        ('submission', 'Submission Discussion'),
    ]
    
    conversation_type = models.CharField(
        max_length=20, 
        choices=CONVERSATION_TYPES, 
        default='direct'
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ConversationParticipant',
        related_name='conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Track who created the conversation (useful for submission conversations)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_conversations',
        help_text='User who initiated this conversation'
    )
    
    # Link to submission for submission conversations
    submission = models.ForeignKey(
        'submissions.Submission',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='conversations'
    )
    
    objects = ConversationManager()
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['conversation_type', '-updated_at']),
            models.Index(fields=['submission', '-updated_at']),
        ]
        constraints = [
            # Ensure only one conversation per submission
            models.UniqueConstraint(
                fields=['submission'],
                condition=models.Q(submission__isnull=False),
                name='unique_submission_conversation'
            )
        ]
    
    def __str__(self):
        if self.conversation_type == 'direct':
            users = list(self.participants.all()[:2])
            if len(users) == 2:
                return f"Conversation: {users[0].username} & {users[1].username}"
        elif self.conversation_type == 'submission' and self.submission:
            # Format: "Project: Project Name (User's Name)"
            content_obj = self.submission.to_project or self.submission.to_task or self.submission.to_need
            content_type = 'Project' if self.submission.to_project else ('Task' if self.submission.to_task else 'Need')
            content_title = getattr(content_obj, 'title', getattr(content_obj, 'name', 'Unknown'))
            
            # Get submitter's display name
            submitter = self.submission.applicant
            submitter_name = submitter.get_full_name() or submitter.username
            
            return f"{content_type}: {content_title} ({submitter_name})"
        return f"Conversation {self.id}"
    
    def get_other_participant(self, user):
        """Get the other participant in a direct conversation"""
        if self.conversation_type not in ['direct', 'submission']:
            return None
            
        participants = list(self.participants.all())
        for participant in participants:
            if participant.id != user.id:
                return participant
        return None
    
    def get_submission_admin(self):
        """Get the admin/project team member for a submission conversation"""
        if self.conversation_type != 'submission' or not self.submission:
            return None
        
        # Return participant who is not the submitter
        participants = list(self.participants.all())
        for participant in participants:
            if participant.id != self.submission.applicant.id:
                return participant
        return None
    
    def get_last_message(self):
        """Get the most recent message in this conversation"""
        return self.messages.order_by('-timestamp').first()
    
    def get_unread_count(self, user):
        """Get count of unread messages for a specific user"""
        try:
            participant = self.conversationparticipant_set.get(user=user)
            if participant.last_read_at:
                return self.messages.filter(
                    timestamp__gt=participant.last_read_at
                ).exclude(sender=user).count()
            else:
                return self.messages.exclude(sender=user).count()
        except ConversationParticipant.DoesNotExist:
            return 0
    
    def is_user_participant(self, user):
        """Check if user is a participant in this conversation"""
        return self.participants.filter(id=user.id).exists()


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('conversation', 'user')
        indexes = [
            models.Index(fields=['user', '-last_read_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} in {self.conversation}"
    
    def mark_as_read(self):
        """Mark conversation as read up to current time"""
        self.last_read_at = timezone.now()
        self.save(update_fields=['last_read_at'])


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
            models.Index(fields=['sender', '-timestamp']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"
    
    def is_read_by(self, user):
        """Check if message has been read by a specific user"""
        if user == self.sender:
            return True  # Sender has always "read" their own message
        
        try:
            participant = self.conversation.conversationparticipant_set.get(user=user)
            return (participant.last_read_at and 
                   participant.last_read_at >= self.timestamp)
        except ConversationParticipant.DoesNotExist:
            return False
    
    def get_read_status(self, current_user):
        """Get read status for display (sent, delivered, read)"""
        if self.sender != current_user:
            return None  # Only show status for own messages
        
        other_participant = self.conversation.get_other_participant(current_user)
        if not other_participant:
            return 'sent'
        
        if self.is_read_by(other_participant):
            return 'read'
        else:
            return 'delivered'  # Assume delivered if user exists