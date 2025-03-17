from django.contrib import admin
from django.utils import timezone
from .models import Comment, CommentReport, CommentVote, CommentReaction

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'content_preview', 'created_at', 'status', 'score', 'total_replies')
    list_filter = ('status', 'created_at', 'is_edited')
    search_fields = ('content', 'user__username', 'author_name')
    readonly_fields = ('created_at', 'updated_at', 'score', 'total_replies')
    raw_id_fields = ('user', 'parent', 'to_project', 'to_task', 'to_need')
    actions = ['approve_comments', 'reject_comments', 'flag_comments']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
    
    def approve_comments(self, request, queryset):
        queryset.update(status='APPROVED', moderated_by=request.user, moderated_at=timezone.now())
        self.message_user(request, f"{queryset.count()} comments have been approved.")
    approve_comments.short_description = "Approve selected comments"
    
    # Add similar methods for reject_comments and flag_comments