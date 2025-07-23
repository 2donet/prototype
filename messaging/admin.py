from django.contrib import admin
from .models import Conversation, ConversationParticipant, Message


class ConversationParticipantInline(admin.TabularInline):
    model = ConversationParticipant
    extra = 0
    readonly_fields = ('joined_at', 'last_read_at')


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('timestamp', 'is_edited', 'edited_at')
    fields = ('sender', 'content', 'timestamp', 'is_edited')
    
    def get_queryset(self, request):
        # Only show last 10 messages to avoid performance issues
        qs = super().get_queryset(request)
        return qs.order_by('-timestamp')[:10]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation_type', 'get_participants', 'created_at', 'updated_at', 'message_count')
    list_filter = ('conversation_type', 'created_at', 'updated_at')
    search_fields = ('participants__username', 'participants__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ConversationParticipantInline, MessageInline]
    
    def get_participants(self, obj):
        return ', '.join([user.username for user in obj.participants.all()])
    get_participants.short_description = 'Participants'
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('participants')


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'conversation', 'joined_at', 'last_read_at', 'is_active')
    list_filter = ('is_active', 'joined_at', 'last_read_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('joined_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'conversation')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'get_conversation_participants', 'timestamp', 'content_preview', 'is_edited')
    list_filter = ('timestamp', 'is_edited', 'conversation__conversation_type')
    search_fields = ('sender__username', 'content', 'conversation__participants__username')
    readonly_fields = ('timestamp', 'edited_at')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    def get_conversation_participants(self, obj):
        return ', '.join([user.username for user in obj.conversation.participants.all()])
    get_conversation_participants.short_description = 'Conversation'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'sender', 'conversation'
        ).prefetch_related('conversation__participants')