# problems/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Problem
from skills.models import Skill
from project.models import Project
from task.models import Task
from need.models import Need

User = get_user_model()


class ProblemForm(forms.ModelForm):
    """Form for creating and editing problems"""
    
    skills = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter skills separated by commas',
            'class': 'materialize-textarea'
        }),
        help_text="Skills related to this problem (comma-separated)"
    )
    
    assigned_to = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select users to assign to this problem"
    )
    
    due_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'datepicker'
        }),
        help_text="Optional deadline for resolving this problem"
    )
    
    class Meta:
        model = Problem
        fields = [
            'name', 'summary', 'desc', 'priority', 'status', 
            'visibility', 'due_date', 'resolution'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter problem title',
                'class': 'validate'
            }),
            'summary': forms.Textarea(attrs={
                'placeholder': 'Brief summary of the problem',
                'class': 'materialize-textarea',
                'rows': 2
            }),
            'desc': forms.Textarea(attrs={
                'placeholder': 'Detailed description of the problem',
                'class': 'materialize-textarea',
                'rows': 6
            }),
            'priority': forms.Select(attrs={
                'class': 'browser-default'
            }),
            'status': forms.Select(attrs={
                'class': 'browser-default'
            }),
            'visibility': forms.Select(attrs={
                'class': 'browser-default'
            }),
            'resolution': forms.Textarea(attrs={
                'placeholder': 'How was this problem resolved?',
                'class': 'materialize-textarea',
                'rows': 4
            }),
        }
        
        help_texts = {
            'name': 'A clear, descriptive title for the problem',
            'summary': 'A brief one-sentence summary',
            'desc': 'Detailed description including steps to reproduce, expected vs actual behavior, etc.',
            'priority': 'How urgent is this problem?',
            'status': 'Current status of the problem',
            'visibility': 'Who can view this problem?',
            'resolution': 'Only fill this if the problem is solved'
        }
    
    def __init__(self, *args, **kwargs):
        self.parent_object = kwargs.pop('parent_object', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # If we have a parent object, we can filter assignable users
        if self.parent_object and isinstance(self.parent_object, Project):
            # Prioritize project members but allow any user
            project_members = User.objects.filter(membership__project=self.parent_object)
            all_users = User.objects.all().order_by('username')
            
            # Create a custom queryset with project members first
            member_ids = list(project_members.values_list('id', flat=True))
            non_members = all_users.exclude(id__in=member_ids)
            
            # Combine querysets
            self.fields['assigned_to'].queryset = project_members.union(non_members)
        
        # If editing, populate skills field
        if self.instance and self.instance.pk:
            skills_list = [skill.name for skill in self.instance.skills.all()]
            self.fields['skills'].initial = ', '.join(skills_list)
            
            # Hide resolution field unless problem is solved
            if self.instance.status != 'solved':
                self.fields['resolution'].widget = forms.HiddenInput()
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError("Problem name is required.")
        return name
    
    def clean_skills(self):
        """Parse and validate skills"""
        skills_str = self.cleaned_data.get('skills', '')
        if not skills_str.strip():
            return []
        
        # Split by comma and clean up
        skill_names = [name.strip() for name in skills_str.split(',') if name.strip()]
        
        # Validate each skill name
        validated_skills = []
        for skill_name in skill_names:
            if len(skill_name) > 50:
                raise ValidationError(f"Skill name '{skill_name}' is too long (max 50 characters)")
            validated_skills.append(skill_name)
        
        return validated_skills
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        resolution = cleaned_data.get('resolution', '').strip()
        
        # If status is solved, require resolution
        if status == 'solved' and not resolution:
            self.add_error('resolution', 'Resolution is required when marking a problem as solved.')
        
        # If status is not solved, clear resolution
        if status != 'solved':
            cleaned_data['resolution'] = ''
        
        return cleaned_data
    
    def save(self, commit=True):
        problem = super().save(commit=False)
        
        # Set parent object if provided
        if self.parent_object:
            if isinstance(self.parent_object, Project):
                problem.to_project = self.parent_object
            elif isinstance(self.parent_object, Task):
                problem.to_task = self.parent_object
            elif isinstance(self.parent_object, Need):
                problem.to_need = self.parent_object
        
        if commit:
            problem.save()
            
            # Handle skills
            skills_data = self.cleaned_data.get('skills', [])
            if skills_data:
                # Clear existing skills and add new ones
                problem.skills.clear()
                for skill_name in skills_data:
                    problem.add_skill(skill_name)
            
            # Handle many-to-many assignments
            self.save_m2m()
        
        return problem


class QuickProblemForm(forms.ModelForm):
    """Simplified form for quick problem creation"""
    
    class Meta:
        model = Problem
        fields = ['name', 'desc', 'priority']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Problem title',
                'class': 'validate'
            }),
            'desc': forms.Textarea(attrs={
                'placeholder': 'Describe the problem',
                'class': 'materialize-textarea',
                'rows': 3
            }),
            'priority': forms.Select(attrs={
                'class': 'browser-default'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.parent_object = kwargs.pop('parent_object', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        problem = super().save(commit=False)
        
        # Set defaults
        problem.status = 'open'
        problem.visibility = 'public'
        
        # Set parent object
        if self.parent_object:
            if isinstance(self.parent_object, Project):
                problem.to_project = self.parent_object
            elif isinstance(self.parent_object, Task):
                problem.to_task = self.parent_object
            elif isinstance(self.parent_object, Need):
                problem.to_need = self.parent_object
        
        if commit:
            problem.save()
        
        return problem


class ProblemAssignmentForm(forms.Form):
    """Form for managing problem assignments"""
    
    users_to_assign = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Assign Users"
    )
    
    users_to_unassign = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Unassign Users"
    )
    
    def __init__(self, *args, **kwargs):
        self.problem = kwargs.pop('problem')
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Set queryset for users to assign (exclude already assigned)
        if self.project:
            available_users = User.objects.filter(
                membership__project=self.project
            ).exclude(
                id__in=self.problem.assigned_to.values_list('id', flat=True)
            )
        else:
            available_users = User.objects.exclude(
                id__in=self.problem.assigned_to.values_list('id', flat=True)
            )
        
        self.fields['users_to_assign'].queryset = available_users
        
        # Set queryset for users to unassign (only currently assigned)
        self.fields['users_to_unassign'].queryset = self.problem.assigned_to.all()
    
    def save(self):
        """Apply the assignment changes"""
        users_to_assign = self.cleaned_data.get('users_to_assign', [])
        users_to_unassign = self.cleaned_data.get('users_to_unassign', [])
        
        # Assign new users
        for user in users_to_assign:
            self.problem.assign_user(user)
        
        # Unassign users
        for user in users_to_unassign:
            self.problem.unassign_user(user)
        
        return self.problem


class ProblemFilterForm(forms.Form):
    """Form for filtering problems in list views"""
    
    status = forms.ChoiceField(
        choices=[('all', 'All Statuses')] + Problem.STATUS_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={'class': 'browser-default'})
    )
    
    priority = forms.ChoiceField(
        choices=[('all', 'All Priorities')] + Problem.PRIORITY_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={'class': 'browser-default'})
    )
    
    assigned = forms.ChoiceField(
        choices=[
            ('all', 'All Problems'),
            ('me', 'Assigned to Me'),
            ('unassigned', 'Unassigned'),
        ],
        required=False,
        initial='all',
        widget=forms.Select(attrs={'class': 'browser-default'})
    )
    
    sort = forms.ChoiceField(
        choices=[
            ('-priority', 'Highest Priority First'),
            ('priority', 'Lowest Priority First'),
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('name', 'Name A-Z'),
            ('-name', 'Name Z-A'),
        ],
        required=False,
        initial='-priority',
        widget=forms.Select(attrs={'class': 'browser-default'})
    )