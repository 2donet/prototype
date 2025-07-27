from django.contrib import admin
from .models import Plan, Step, PlanSuggestion


class StepInline(admin.TabularInline):
    model = Step
    extra = 1
    ordering = ['order']
    fields = ['name', 'desc', 'order']


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'step_count', 'is_template']
    list_filter = ['is_template', 'created_at', 'created_by']
    search_fields = ['name', 'desc']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [StepInline]
    
    fieldsets = (
        ('Plan Information', {
            'fields': ('name', 'desc', 'created_by', 'is_template')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def step_count(self, obj):
        return obj.steps.count()
    step_count.short_description = 'Steps'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan', 'order']
    list_filter = ['plan']
    search_fields = ['name', 'desc', 'plan__name']
    ordering = ['plan', 'order']
    
    fieldsets = (
        ('Step Information', {
            'fields': ('plan', 'name', 'desc', 'order')
        }),
    )


@admin.register(PlanSuggestion)
class PlanSuggestionAdmin(admin.ModelAdmin):
    list_display = ['plan', 'content_object', 'status', 'suggested_by', 'created_at']
    list_filter = ['status', 'created_at', 'content_type']
    search_fields = ['plan__name', 'suggested_by__username', 'suggestion_note']
    readonly_fields = ['created_at', 'reviewed_at']
    
    fieldsets = (
        ('Suggestion Information', {
            'fields': ('plan', 'content_type', 'object_id', 'status')
        }),
        ('Users', {
            'fields': ('suggested_by', 'reviewed_by')
        }),
        ('Notes', {
            'fields': ('suggestion_note', 'review_note')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'reviewed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing object
            readonly.extend(['plan', 'content_type', 'object_id', 'suggested_by'])
        return readonly
    
    actions = ['approve_suggestions', 'reject_suggestions']
    
    def approve_suggestions(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='approved',
            reviewed_by=request.user
        )
        self.message_user(request, f'{updated} suggestions approved.')
    approve_suggestions.short_description = 'Approve selected suggestions'
    
    def reject_suggestions(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user
        )
        self.message_user(request, f'{updated} suggestions rejected.')
    reject_suggestions.short_description = 'Reject selected suggestions'