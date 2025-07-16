from django import forms
from .models import Task
from skills.models import Skill

class TaskForm(forms.ModelForm):
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'browser-default'})
    )

    class Meta:
        model = Task
        fields = ['name', 'desc', 'priority', 'to_project', 'to_task', 'skills']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'validate'}),
            'desc': forms.Textarea(attrs={'class': 'materialize-textarea'}),
            'priority': forms.NumberInput(attrs={'class': 'validate'}),
            'to_project': forms.Select(attrs={'class': 'browser-default'}),
            'to_task': forms.Select(attrs={'class': 'browser-default'}),
        }
        labels = {
            'name': 'Task Name',
            'desc': 'Description',
            'to_project': 'Related Project',
            'to_task': 'Parent Task',
        }