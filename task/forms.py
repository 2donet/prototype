from django import forms
from .models import Task
from skills.models import Skill
from project.models import Project
from django.utils import timezone
from django.db import models
import json

class TaskForm(forms.ModelForm):
    # Change skills to handle chips input
    skills_input = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Enter skills required for this task (up to 20)"
    )
    
    due_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={
                'class': 'validate',
                'type': 'datetime-local'
            }
        ),
        help_text="When should this task be completed?"
    )
    
    estimated_hours = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=1000,
        widget=forms.NumberInput(attrs={'class': 'validate', 'min': '1', 'max': '1000'}),
        help_text="Estimated hours to complete this task"
    )
    
    actual_hours = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=1000,
        widget=forms.NumberInput(attrs={'class': 'validate', 'min': '0', 'max': '1000'}),
        help_text="Actual hours spent on this task"
    )

    class Meta:
        model = Task
        fields = [
            'name', 'desc', 'priority', 'status', 'due_date',
            'estimated_hours', 'actual_hours', 'to_project', 'to_task', 'skills_input',
            'allow_anonymous_comments', 'require_comment_approval'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'validate', 'maxlength': '50'}),
            'desc': forms.Textarea(attrs={'class': 'materialize-textarea'}),
            'priority': forms.Select(attrs={'class': 'browser-default'}),
            'status': forms.Select(attrs={'class': 'browser-default'}),
            'to_project': forms.Select(attrs={'class': 'browser-default'}),
            'to_task': forms.Select(attrs={'class': 'browser-default'}),
            'allow_anonymous_comments': forms.CheckboxInput(attrs={'class': 'filled-in'}),
            'require_comment_approval': forms.CheckboxInput(attrs={'class': 'filled-in'}),
        }
        labels = {
            'name': 'Task Name',
            'desc': 'Description',
            'priority': 'Priority Level',
            'status': 'Current Status',
            'to_project': 'Related Project',
            'to_task': 'Parent Task',
            'allow_anonymous_comments': 'Allow Anonymous Comments',
            'require_comment_approval': 'Require Comment Approval',
        }
        help_texts = {
            'name': 'Brief, descriptive name for the task (max 50 characters)',
            'desc': 'Detailed description of what needs to be done',
            'priority': 'How important is this task?',
            'status': 'Current state of the task',
            'to_project': 'Which project does this task belong to?',
            'to_task': 'Is this a subtask of another task?',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # CRITICAL FIX: Load ALL existing skills into the form
        if self.instance and self.instance.pk:
            # Get existing skills as objects with both name and id
            existing_skills = list(self.instance.skills.all())
            print(f"DEBUG FORM INIT: Task {self.instance.pk} has {len(existing_skills)} skills: {[s.name for s in existing_skills]}")
            
            # Format as objects with name and id for better handling
            skills_data = [{'name': skill.name, 'id': skill.id} for skill in existing_skills]
            skills_json = json.dumps(skills_data)
            
            # Set both initial value and widget value to ensure it's available to frontend
            self.fields['skills_input'].initial = skills_json
            self.fields['skills_input'].widget.attrs['value'] = skills_json
            
            print(f"DEBUG FORM INIT: Set skills_input to: {skills_json}")
        else:
            # For new tasks, ensure empty array
            self.fields['skills_input'].initial = json.dumps([])
            self.fields['skills_input'].widget.attrs['value'] = json.dumps([])
            print("DEBUG FORM INIT: New task, set skills to empty array")
        
        # Filter projects based on user permissions
        if user:
            if user.is_staff or user.is_superuser:
                # Staff can see all projects
                self.fields['to_project'].queryset = Project.objects.all()
                self.fields['to_task'].queryset = Task.objects.all()
            else:
                # Regular users can only see public projects and their own
                self.fields['to_project'].queryset = Project.objects.filter(
                    models.Q(visibility='public') | 
                    models.Q(created_by=user)
                ).distinct()
                
                # Can only select tasks from visible projects or their own tasks
                self.fields['to_task'].queryset = Task.objects.filter(
                    models.Q(to_project__visibility='public') |
                    models.Q(to_project__created_by=user) |
                    models.Q(created_by=user)
                ).distinct()
        
        # If editing existing task, filter parent task to prevent circular references
        if self.instance and self.instance.pk:
            # Exclude self and any descendants to prevent circular references
            excluded_ids = [self.instance.pk]
            excluded_ids.extend(self.get_descendant_ids(self.instance))
            self.fields['to_task'].queryset = self.fields['to_task'].queryset.exclude(
                id__in=excluded_ids
            )
            
        # Add empty option for optional fields
        self.fields['to_project'].empty_label = "No Project"
        self.fields['to_task'].empty_label = "No Parent Task"
        
        # Set default due date to one week from now
        if not self.instance.pk and not self.initial.get('due_date'):
            self.fields['due_date'].initial = timezone.now() + timezone.timedelta(days=7)

    def get_descendant_ids(self, task, visited=None):
        """Get all descendant task IDs to prevent circular references"""
        if visited is None:
            visited = set()
        
        if task.id in visited:
            return []
        
        visited.add(task.id)
        descendant_ids = []
        
        # Get direct children
        children = Task.objects.filter(to_task=task)
        for child in children:
            descendant_ids.append(child.id)
            # Recursively get grandchildren
            descendant_ids.extend(self.get_descendant_ids(child, visited))
        
        return descendant_ids

    def clean_skills_input(self):
        """Process skills from chips input and validate - IMPROVED VERSION"""
        skills_input = self.cleaned_data.get('skills_input', '')
        
        print(f"DEBUG CLEAN: Raw skills_input: {repr(skills_input)}")
        print(f"DEBUG CLEAN: Type: {type(skills_input)}")
        
        if not skills_input or skills_input.strip() == '' or skills_input.strip() == '[]':
            print("DEBUG CLEAN: Skills input is empty or empty array, returning []")
            return []
        
        try:
            # Parse JSON data from chips input
            skills_data = json.loads(skills_input) if skills_input else []
            print(f"DEBUG CLEAN: Parsed JSON successfully: {skills_data}")
            
            # Ensure it's a list
            if not isinstance(skills_data, list):
                print(f"DEBUG CLEAN: Not a list, converting: {skills_data}")
                skills_data = []
            
            # Process different formats that might come from frontend
            processed_skills = []
            for item in skills_data:
                if isinstance(item, dict) and 'name' in item:
                    # Format: {'name': 'Python', 'id': 1} or {'name': 'Python'}
                    skill_name = item['name'].strip()
                elif isinstance(item, str):
                    # Format: 'Python'
                    skill_name = item.strip()
                else:
                    # Skip invalid items
                    print(f"DEBUG CLEAN: Skipping invalid skill item: {item}")
                    continue
                
                if skill_name:
                    processed_skills.append(skill_name)
            
            print(f"DEBUG CLEAN: Processed skill names: {processed_skills}")
            
            # Remove duplicates while preserving order
            unique_skills = []
            seen = set()
            for skill in processed_skills:
                if skill.lower() not in seen:
                    unique_skills.append(skill)
                    seen.add(skill.lower())
            
            print(f"DEBUG CLEAN: Unique skills: {unique_skills}")
            
            if len(unique_skills) > 20:
                print(f"DEBUG CLEAN: Too many skills: {len(unique_skills)}")
                raise forms.ValidationError("A task can have a maximum of 20 skills.")
            
            # Get or create skill objects
            skill_objects = []
            for skill_name in unique_skills:
                skill_name_clean = skill_name.strip()
                if skill_name_clean:
                    try:
                        skill = Skill.objects.get(name__iexact=skill_name_clean)
                        print(f"DEBUG CLEAN: Found existing skill: {skill.name}")
                    except Skill.DoesNotExist:
                        skill = Skill.objects.create(name=skill_name_clean.title())
                        print(f"DEBUG CLEAN: Created new skill: {skill.name}")
                    skill_objects.append(skill)
            
            print(f"DEBUG CLEAN: Final skill objects: {[s.name for s in skill_objects]}")
            return skill_objects
            
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"DEBUG CLEAN: JSON parsing failed: {e}")
            # If JSON parsing fails, try to parse as comma-separated string
            try:
                skill_names = [name.strip() for name in str(skills_input).split(',') if name.strip()]
                print(f"DEBUG CLEAN: Trying comma-separated: {skill_names}")
                
                if len(skill_names) > 20:
                    raise forms.ValidationError("A task can have a maximum of 20 skills.")
                
                skill_objects = []
                for skill_name in skill_names:
                    if skill_name:
                        try:
                            skill = Skill.objects.get(name__iexact=skill_name)
                        except Skill.DoesNotExist:
                            skill = Skill.objects.create(name=skill_name.title())
                        skill_objects.append(skill)
                
                print(f"DEBUG CLEAN: Comma-separated result: {[s.name for s in skill_objects]}")
                return skill_objects
            except Exception as fallback_error:
                print(f"DEBUG CLEAN: Fallback parsing also failed: {fallback_error}")
                # If all parsing fails, return empty list (don't raise error)
                print("DEBUG CLEAN: Returning empty list as fallback")
                return []

    def clean_due_date(self):
        """Validate due date is in the future for new tasks"""
        due_date = self.cleaned_data.get('due_date')
        if due_date and not self.instance.pk:  # Only for new tasks
            if due_date <= timezone.now():
                raise forms.ValidationError("Due date must be in the future.")
        return due_date

    def clean_actual_hours(self):
        """Validate actual hours don't exceed estimated hours by too much"""
        actual_hours = self.cleaned_data.get('actual_hours')
        estimated_hours = self.cleaned_data.get('estimated_hours')
        
        if actual_hours and estimated_hours:
            if actual_hours > estimated_hours * 2:
                # Warning, not error - sometimes tasks take longer than expected
                pass  # Could add a warning message here
        
        return actual_hours

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        to_project = cleaned_data.get('to_project')
        to_task = cleaned_data.get('to_task')
        
        print(f"DEBUG CLEAN: to_project={to_project}, type={type(to_project)}")
        
        # If parent task is selected, ensure it belongs to the same project
        if to_task and to_project:  # Only if both are truthy
            if to_task.to_project and to_task.to_project != to_project:
                raise forms.ValidationError({
                    'to_task': 'Parent task must belong to the same project.'
                })
        
        # More precise check for empty to_project
        if to_task and (to_project is None or to_project == ''):
            if to_task.main_project:
                cleaned_data['main_project'] = to_task.main_project
                # Explicitly set to_project to None
                cleaned_data['to_project'] = None
                print(f"DEBUG CLEAN: Inherited main_project={to_task.main_project}")
        
        return cleaned_data

class TaskFilterForm(forms.Form):
    """Form for handling task filtering parameters"""
    
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search tasks, descriptions, skills...',
            'class': 'validate'
        })
    )
    
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'browser-default'})
    )
    
    skills = forms.CharField(
        required=False,
        widget=forms.HiddenInput()  # Will be handled by chips input
    )
    
    skill_logic = forms.ChoiceField(
        choices=[('any', 'Any selected skill'), ('all', 'All selected skills')],
        initial='any',
        required=False,
        widget=forms.RadioSelect()
    )
    
    statuses = forms.MultipleChoiceField(
        choices=Task.STATUS_CHOICES,
        required=False,
        initial=['todo', 'in_progress', 'review'],
        widget=forms.CheckboxSelectMultiple()
    )
    
    priorities = forms.MultipleChoiceField(
        choices=Task.PRIORITY_CHOICES,
        required=False,
        initial=[1, 2, 3, 4],
        widget=forms.CheckboxSelectMultiple()
    )
    
    created_after = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'validate'})
    )
    
    due_before = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'validate'})
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('-priority', 'Priority (High to Low)'),
            ('priority', 'Priority (Low to High)'),
            ('due_date', 'Due Date (Nearest)'),
            ('-due_date', 'Due Date (Furthest)'),
            ('name', 'Name (A-Z)'),
            ('-name', 'Name (Z-A)'),
            ('status', 'Status'),
        ],
        initial='-created_at',
        required=False,
        widget=forms.Select(attrs={'class': 'browser-default'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter projects based on user permissions
        if user:
            if user.is_staff or user.is_superuser:
                self.fields['projects'].queryset = Project.objects.all()
            else:
                from django.db import models
                self.fields['projects'].queryset = Project.objects.filter(
                    models.Q(visibility='public') | 
                    models.Q(created_by=user)
                ).distinct()


class QuickTaskUpdateForm(forms.Form):
    """Form for quick AJAX task updates"""
    
    field = forms.ChoiceField(
        choices=[
            ('status', 'Status'),
            ('priority', 'Priority'),
        ],
        required=True
    )
    
    value = forms.CharField(required=True)
    
    def clean(self):
        cleaned_data = super().clean()
        field = cleaned_data.get('field')
        value = cleaned_data.get('value')
        
        if field == 'status':
            if value not in ['todo', 'in_progress', 'review', 'completed']:
                raise forms.ValidationError({'value': 'Invalid status value'})
        elif field == 'priority':
            try:
                priority = int(value)
                if priority not in [1, 2, 3, 4]:
                    raise forms.ValidationError({'value': 'Priority must be between 1 and 4'})
            except (ValueError, TypeError):
                raise forms.ValidationError({'value': 'Priority must be a number'})
        
        return cleaned_data