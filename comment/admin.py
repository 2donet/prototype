from django.contrib import admin
from .models import (
    Comment, CommentReport, CommentVote, 
    ModerationAction, CommentReportGroup
)


class CommentReportInline(admin.TabularInline):
    model = CommentReport
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


class ModerationActionInline(admin.TabularInline):
    model = ModerationAction
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'content_preview', 'user', 'status', 'score', 'created_at')
    list_filter = ('status', 'created_at', 'is_edited')
    search_fields = ('content', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'score')
    inlines = [CommentReportInline, ModerationActionInline]
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"


@admin.register(CommentReport)
class CommentReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'comment_preview', 'report_type', 'reportee', 'status', 'created_at')
    list_filter = ('report_type', 'status', 'created_at')
    search_fields = ('comment__content', 'description', 'reportee__username')
    readonly_fields = ('created_at', 'updated_at')
    
    def comment_preview(self, obj):
        return obj.comment.content[:30] + "..." if len(obj.comment.content) > 30 else obj.comment.content
    comment_preview.short_description = "Comment"


@admin.register(ModerationAction)
class ModerationActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'decision', 'comment_preview', 'moderator', 'decision_scope', 'created_at')
    list_filter = ('decision', 'decision_scope', 'created_at', 'escalate_to_platform')
    search_fields = ('reason', 'comment__content', 'moderator__username')
    readonly_fields = ('created_at',)
    
    def comment_preview(self, obj):
        return obj.comment.content[:30] + "..." if len(obj.comment.content) > 30 else obj.comment.content
    comment_preview.short_description = "Comment"


@admin.register(CommentReportGroup)
class CommentReportGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'comment_preview', 'total_reports', 'report_types_display', 'status', 'last_reported_at')
    list_filter = ('status', 'total_reports', 'last_reported_at')
    search_fields = ('comment__content',)
    readonly_fields = ('total_reports', 'report_types_summary', 'first_reported_at', 'last_reported_at')
    
    def comment_preview(self, obj):
        return obj.comment.content[:30] + "..." if len(obj.comment.content) > 30 else obj.comment.content
    comment_preview.short_description = "Comment"
    
    def report_types_display(self, obj):
        return obj.get_report_types_display()
    report_types_display.short_description = "Report Types"


@admin.register(CommentVote)
class CommentVoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'comment_preview', 'user', 'vote_type', 'created_at')
    list_filter = ('vote_type', 'created_at')
    search_fields = ('comment__content', 'user__username')
    
    def comment_preview(self, obj):
        return obj.comment.content[:30] + "..." if len(obj.comment.content) > 30 else obj.comment.content
    comment_preview.short_description = "Comment"