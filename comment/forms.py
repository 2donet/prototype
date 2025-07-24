# comment/forms.py
from django import forms
from django.utils import timezone
from .models import (
    CommentReport, ReportType, ModerationAction, 
    ModerationDecision, DecisionScope, ModeratorLevel
)
from .utils import get_moderator_level


class CommentReportForm(forms.ModelForm):
    """Form for users to report comments"""
    
    report_type = forms.ChoiceField(
        choices=ReportType.choices,
        widget=forms.RadioSelect,
        required=True,
        help_text="Select the reason for reporting this comment"
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Please provide additional details about why you are reporting this comment...'
        }),
        required=False,
        help_text="Optional: Provide more context to help moderators understand the issue"
    )
    
    class Meta:
        model = CommentReport
        fields = ['report_type', 'description']
        
    def __init__(self, *args, **kwargs):
        self.comment = kwargs.pop('comment', None)
        self.reportee = kwargs.pop('reportee', None)
        super().__init__(*args, **kwargs)
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set the comment and reportee
        if self.comment:
            instance.comment = self.comment
        
        # Set the reportee if available (authenticated user)
        if self.reportee:
            instance.reportee = self.reportee
            
        # Automatically set the reported user if the comment has a user
        if instance.comment and instance.comment.user:
            instance.reported = instance.comment.user
            
        if commit:
            instance.save()
        return instance


class ModeratorReviewForm(forms.ModelForm):
    """Form for moderators to review and update reports"""
    
    status = forms.ChoiceField(
        choices=[
            ('REVIEWED', 'Mark as Reviewed'),
            ('REJECTED', 'Reject Report'),
            ('RESOLVED', 'Resolve Issue')
        ],
        widget=forms.RadioSelect,
        required=True
    )
    
    moderator_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        help_text="Notes visible only to moderators"
    )
    
    class Meta:
        model = CommentReport
        fields = ['status', 'moderator_notes']
        
    def __init__(self, *args, **kwargs):
        self.moderator = kwargs.pop('moderator', None)
        super().__init__(*args, **kwargs)
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set the reviewer
        if self.moderator:
            instance.reviewed_by = self.moderator
            
        if commit:
            instance.save()
        return instance


class ModerationActionForm(forms.ModelForm):
    """Enhanced form for moderators to take action on reported comments"""
    
    decision = forms.ChoiceField(
        choices=ModerationDecision.choices,
        widget=forms.RadioSelect,
        required=True,
        help_text="Select the action to take"
    )
    
    decision_scope = forms.ChoiceField(
        choices=DecisionScope.choices,
        widget=forms.RadioSelect,
        initial=DecisionScope.ALL_REPORTS,
        help_text="Choose which reports this decision applies to"
    )
    
    target_report_type = forms.ChoiceField(
        choices=ReportType.choices,
        required=False,
        widget=forms.Select(attrs={'class': 'browser-default'}),
        help_text="Only used when applying to specific report type"
    )
    
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'materialize-textarea'}),
        help_text="Explain your decision for the audit trail"
    )
    
    new_content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6, 'class': 'materialize-textarea'}),
        required=False,
        help_text="New content (only for EDIT decisions)"
    )
    
    notify_reporters = forms.BooleanField(
        initial=True,
        required=False,
        help_text="Notify users who filed reports about this decision"
    )
    
    escalate_to_platform = forms.BooleanField(
        initial=False,
        required=False,
        help_text="Report this to platform-wide moderation"
    )
    
    suspension_days = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=365,
        widget=forms.NumberInput(attrs={'class': 'validate'}),
        help_text="Days to suspend user (only for SUSPEND_USER decisions)"
    )
    
    class Meta:
        model = ModerationAction
        fields = [
            'decision', 'decision_scope', 'target_report_type', 
            'reason', 'new_content', 'notify_reporters', 
            'escalate_to_platform'
        ]
    
    def __init__(self, *args, **kwargs):
        self.comment = kwargs.pop('comment', None)
        self.moderator = kwargs.pop('moderator', None)
        super().__init__(*args, **kwargs)
        
        # Customize choices based on moderator level
        if self.moderator:
            from .views import get_moderator_level
            moderator_level = get_moderator_level(self.moderator)
            if moderator_level == ModeratorLevel.JUNIOR:
                # Junior moderators can't ban users or edit content
                restricted_choices = [
                    choice for choice in ModerationDecision.choices 
                    if choice[0] not in [ModerationDecision.BAN_USER, ModerationDecision.EDIT]
                ]
                self.fields['decision'].choices = restricted_choices
    
    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        decision_scope = cleaned_data.get('decision_scope')
        target_report_type = cleaned_data.get('target_report_type')
        new_content = cleaned_data.get('new_content')
        
        # Validate scope-specific fields
        if decision_scope == DecisionScope.REPORT_TYPE and not target_report_type:
            raise forms.ValidationError("Report type is required when applying to specific report type.")
        
        # Validate content for EDIT decisions
        if decision == ModerationDecision.EDIT and not new_content:
            raise forms.ValidationError("New content is required for EDIT decisions.")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set suspension date if needed
        suspension_days = self.cleaned_data.get('suspension_days')
        if instance.decision == ModerationDecision.SUSPEND_USER and suspension_days:
            instance.suspension_until = timezone.now() + timezone.timedelta(days=suspension_days)
        
        if commit:
            instance.save()
        return instance

