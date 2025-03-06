from django import forms
from .models import CommentReport, ReportType


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