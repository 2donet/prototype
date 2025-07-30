from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from .models import Need
from skills.models import Skill


class NeedForm(forms.ModelForm):
    """Form for creating and editing needs"""
    
    # Custom fields that aren't directly on the model
    estimated_time_hours = forms.FloatField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'step': '0.5'}),
        help_text="How long do you estimate this will take?"
    )
    
    required_skills = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Skills will be handled by JavaScript chips"
    )
    
    class Meta:
        model = Need
        fields = [
            'name', 'desc', 'priority', 'status', 'visibility',
            'skill_level', 'resources', 'deadline', 'cost_estimate',
            'is_remote', 'is_stationary', 'documentation_url',
            'completion_notes', 'progress'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'maxlength': 50,
                'required': True,
                'class': 'validate'
            }),
            'desc': forms.Textarea(attrs={
                'class': 'materialize-textarea'
            }),
            'priority': forms.Select(choices=[
                (0, 'Minimal (0-24)'),
                (25, 'Low (25-49)'),
                (50, 'Medium (50-74)'),
                (75, 'High (75-100)')
            ]),
            'status': forms.Select(choices=[
                ('pending', 'Pending'),
                ('in_progress', 'In Progress'),
                ('fulfilled', 'Fulfilled'),
                ('canceled', 'Canceled')
            ]),
            'visibility': forms.Select(choices=[
                ('public', 'Public'),
                ('members', 'Project Members Only'),
                ('admins', 'Admins Only')
            ]),
            'skill_level': forms.Select(choices=[
                ('', 'Not Specified'),
                ('beginner', 'Beginner'),
                ('intermediate', 'Intermediate'),
                ('advanced', 'Advanced'),
                ('expert', 'Expert')
            ]),
            'deadline': forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }),
            'cost_estimate': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0'
            }),
            'resources': forms.Textarea(attrs={
                'class': 'materialize-textarea'
            }),
            'documentation_url': forms.URLInput(),
            'completion_notes': forms.Textarea(attrs={
                'class': 'materialize-textarea'
            }),
            'progress': forms.NumberInput(attrs={
                'type': 'range',
                'min': '0',
                'max': '100'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Make desc and progress fields not required
        self.fields['desc'].required = False
        self.fields['progress'].required = False
        self.fields['completion_notes'].required = False
        
        # Set default values for create mode
        if not self.instance or not self.instance.pk:
            self.fields['progress'].initial = 0
            self.fields['status'].initial = 'pending'
            self.fields['priority'].initial = 50
            self.fields['visibility'].initial = 'public'
            # Hide completion_notes in create mode
            self.fields['completion_notes'].widget = forms.HiddenInput()
        
        # If editing an existing need, populate estimated_time_hours
        if self.instance and self.instance.pk and hasattr(self.instance, 'estimated_time') and self.instance.estimated_time:
            total_seconds = self.instance.estimated_time.total_seconds()
            hours = round((total_seconds / 3600) * 10) / 10  # Round to 1 decimal
            self.fields['estimated_time_hours'].initial = hours

    def clean_deadline(self):
        """Clean and validate deadline field"""
        deadline = self.cleaned_data.get('deadline')
        if deadline:
            # Ensure timezone awareness
            if timezone.is_naive(deadline):
                deadline = timezone.make_aware(deadline)
            
            # Validate deadline is not in the past (optional)
            if deadline < timezone.now():
                raise ValidationError("Deadline cannot be in the past.")
                
        return deadline

    def clean_estimated_time_hours(self):
        """Convert hours to timedelta"""
        hours = self.cleaned_data.get('estimated_time_hours')
        if hours is not None:
            if hours < 0:
                raise ValidationError("Estimated time cannot be negative.")
            return timedelta(hours=hours)
        return None

    def clean_cost_estimate(self):
        """Validate cost estimate"""
        cost = self.cleaned_data.get('cost_estimate')
        if cost is not None and cost < 0:
            raise ValidationError("Cost estimate cannot be negative.")
        return cost

    def clean_name(self):
        """Clean and validate name field"""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if not name:
                raise ValidationError("Name cannot be empty or just whitespace.")
        return name

    def clean(self):
        """Additional form-level validation"""
        cleaned_data = super().clean()
        
        # Validate work type options
        is_remote = cleaned_data.get('is_remote')
        is_stationary = cleaned_data.get('is_stationary')
        
        if not is_remote and not is_stationary:
            # It's okay to have neither specified
            pass
        
        return cleaned_data

    def _process_skills(self, skill_names):
        """Process skills from form data"""
        skills = []
        for skill_name in skill_names:
            skill_name = skill_name.strip()
            if skill_name:
                skill = Skill.get_or_create_skill(skill_name)
                skills.append(skill)
        return skills

    def save(self, commit=True):
        """Custom save method to handle additional processing"""
        need = super().save(commit=False)
        
        # Set the user and project if provided
        if self.user:
            need.created_by = self.user
        if self.project:
            need.to_project = self.project
            
        # Handle estimated_time conversion
        estimated_time = self.clean_estimated_time_hours()
        if estimated_time is not None:
            need.estimated_time = estimated_time
            
        if commit:
            need.save()
            self.save_m2m()
            
            # Handle skills separately since they come from POST data
            # This will be called from the view with the skills data
            
        return need

    def save_skills(self, skill_names):
        """Save skills for the need"""
        if not self.instance:
            return
            
        if skill_names:
            skills = self._process_skills(skill_names)
            self.instance.required_skills.set(skills)
        else:
            # Clear skills if no names provided (maintain old behavior)
            self.instance.required_skills.clear()


class NeedEditForm(NeedForm):
    """Extended form for editing needs with additional fields"""
    
    depends_on = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Dependencies will be handled by JavaScript chips"
    )
    
    related_needs = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Related needs will be handled by JavaScript chips"
    )

    def __init__(self, *args, **kwargs):
        self.available_needs = kwargs.pop('available_needs', None)
        super().__init__(*args, **kwargs)

    def _process_need_relationships(self, need_names, available_needs):
        """Process need names into Need objects using batch filtering like old view"""
        if not need_names:
            return []
            
        # Use batch filtering like the old view for better performance
        needs = available_needs.filter(name__in=need_names)
        return list(needs)

    def save_relationships(self, depends_on_names=None, related_needs_names=None):
        """Save need relationships"""
        if not self.instance or not self.available_needs:
            return
            
        # Handle dependencies - clear if empty list provided
        if depends_on_names is not None:
            if depends_on_names:
                dependencies = self._process_need_relationships(depends_on_names, self.available_needs)
                self.instance.depends_on.set(dependencies)
            else:
                self.instance.depends_on.clear()
            
        # Handle related needs - clear if empty list provided  
        if related_needs_names is not None:
            if related_needs_names:
                related = self._process_need_relationships(related_needs_names, self.available_needs)
                self.instance.related_needs.set(related)
            else:
                self.instance.related_needs.clear()

    def save_with_progress_update(self, user, commit=True):
        """Custom save method that handles progress updates properly"""
        need = super().save(commit=False)
        
        # Handle progress update using the model's method if it exists
        if hasattr(need, 'update_progress') and 'progress' in self.changed_data:
            progress = self.cleaned_data.get('progress')
            completion_notes = self.cleaned_data.get('completion_notes', '')
            if progress is not None:
                need.update_progress(progress, user, completion_notes)
                # Don't set progress again since update_progress handles it
                if commit:
                    need.save()
                    self.save_m2m()
                return need
        
        # Standard save if no progress update needed
        if commit:
            need.save()
            self.save_m2m()
            
        return need