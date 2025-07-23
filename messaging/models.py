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
    
    objects = ConversationManager()
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['conversation_type', '-updated_at']),
        ]
    
    def __str__(self):
        if self.conversation_type == 'direct':
            users = list(self.participants.all()[:2])
            if len(users) == 2:
                return f"Conversation: {users[0].username} & {users[1].username}"
        return f"Conversation {self.id}"
    
    def get_other_participant(self, user):
        """Get the other participant in a direct conversation"""
        if self.conversation_type != 'direct':
            return None
            
        participants = list(self.participants.all())
        for participant in participants:
            if participant.id != user.id:
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