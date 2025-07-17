

from django import forms
from skills.models import Skill
from submissions.models import Submission


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['to_project', 'to_task', 'why_fit', 'relevant_skills', 'additional_info']
        widgets = {
            'to_project': forms.Select(attrs={'class': 'browser-default'}),
            'to_task': forms.Select(attrs={'class': 'browser-default'}),
            'why_fit': forms.Textarea(attrs={
                'class': 'materialize-textarea',
                'placeholder': 'Explain why you are a good fit for this task or project.'
            }),
            'relevant_skills': forms.SelectMultiple(attrs={'class': 'browser-default'}),
            'additional_info': forms.Textarea(attrs={
                'class': 'materialize-textarea',
                'placeholder': 'Any other information you want to share?'
            }),
        }
        labels = {
            'to_project': 'Project',
            'to_task': 'Task',
            'why_fit': 'Why do you fit this task?',
            'relevant_skills': 'Relevant Skills',
            'additional_info': 'Additional Information',
        }
        help_texts = {
            'why_fit': 'Briefly describe your interest and qualifications.',
            'relevant_skills': 'Select skills from the list that are most relevant.',
            'additional_info': 'Provide any additional details or links (e.g., portfolio, LinkedIn).',
        }