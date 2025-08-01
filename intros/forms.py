from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Intro, IntroRelation


class IntroForm(forms.ModelForm):
    """Form for creating and editing intros"""
    
    class Meta:
        model = Intro
        fields = [
            'name', 'summary', 'desc', 'intro_type', 
            'status', 'visibility', 'order', 'main_project'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a descriptive title...'
            }),
            'summary': forms.Textarea(attrs={
                'class': 'form-control materialize-textarea',
                'rows': 3,
                'placeholder': 'Brief summary for listings and previews...'
            }),
            'desc': forms.Textarea(attrs={
                'class': 'form-control materialize-textarea',
                'rows': 8,
                'placeholder': 'Full detailed description...'
            }),
            'intro_type': forms.Select(attrs={
                'class': 'form-control browser-default'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control browser-default'
            }),
            'visibility': forms.Select(attrs={
                'class': 'form-control browser-default'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'main_project': forms.Select(attrs={
                'class': 'form-control browser-default'
            }),
        }
        help_texts = {
            'name': 'A clear, descriptive title for this introduction',
            'summary': 'Brief summary shown in listings (max 500 characters)',
            'desc': 'Full content of the introduction',
            'intro_type': 'What type of introduction is this?',
            'status': 'Publication status - only published intros are visible to most users',
            'visibility': 'Who can view this introduction',
            'order': 'Display order - higher numbers appear first',
            'main_project': 'Main project context for organization and permissions',
        }
    
    def __init__(self, *args, **kwargs):
        self.entity_type = kwargs.pop('entity_type', None)
        self.entity_id = kwargs.pop('entity_id', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Customize main_project queryset based on user permissions
        if 'main_project' in self.fields and self.user:
            from project.models import Project, Membership
            
            # Get projects user can access
            user_projects = Project.objects.filter(
                Q(created_by=self.user) |
                Q(membership__user=self.user)
            ).distinct()
            
            self.fields['main_project'].queryset = user_projects
            self.fields['main_project'].empty_label = "No main project"
            
            # If creating for a specific entity, try to set default main_project
            if self.entity_type and self.entity_id:
                entity_project = self.get_entity_project()
                if entity_project and entity_project in user_projects:
                    self.fields['main_project'].initial = entity_project
        
        # Set helpful placeholders based on context
        if self.entity_type and self.entity_id:
            entity_name = self.get_entity_name()
            if entity_name:
                self.fields['name'].widget.attrs['placeholder'] = f'Introduction for {entity_name}...'
        
        # Restrict visibility choices for non-project-members
        if 'visibility' in self.fields:
            # Everyone can create public and logged_in intros
            choices = [
                ('public', 'Public'),
                ('logged_in', 'Only Logged-In Users'),
            ]
            
            # Only add restricted/private if user has a main project
            if self.fields['main_project'].queryset.exists():
                choices.extend([
                    ('restricted', 'Restricted (Project Members Only)'),
                    ('private', 'Private (Author Only)'),
                ])
            
            self.fields['visibility'].choices = choices
    
    def get_entity_project(self):
        """Get the project associated with the entity"""
        if not self.entity_type or not self.entity_id:
            return None
        
        model_mapping = {
            'task': 'task.Task',
            'project': 'project.Project',
            'need': 'need.Need',
            'problem': 'problems.Problem',
            'plan': 'plans.Plan'
        }
        
        try:
            app_label, model_name = model_mapping[self.entity_type].split('.')
            model = apps.get_model(app_label, model_name)
            entity = model.objects.get(pk=self.entity_id)
            
            if hasattr(entity, 'to_project'):
                return entity.to_project
            elif entity.__class__.__name__ == 'Project':
                return entity
        except (KeyError, model.DoesNotExist):
            pass
        
        return None
    
    def get_entity_name(self):
        """Get the name of the entity this intro is for"""
        if not self.entity_type or not self.entity_id:
            return None
        
        model_mapping = {
            'task': 'task.Task',
            'project': 'project.Project',
            'need': 'need.Need',
            'problem': 'problems.Problem',
            'plan': 'plans.Plan'
        }
        
        try:
            app_label, model_name = model_mapping[self.entity_type].split('.')
            model = apps.get_model(app_label, model_name)
            entity = model.objects.get(pk=self.entity_id)
            return str(entity)
        except (KeyError, model.DoesNotExist):
            return None
    
    def clean_summary(self):
        """Validate summary length"""
        summary = self.cleaned_data.get('summary')
        if summary and len(summary) > 500:
            raise ValidationError('Summary must be 500 characters or less.')
        return summary
    
    def clean_name(self):
        """Validate and clean the name field"""
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError('Name is required.')
        
        # Strip extra whitespace
        name = ' '.join(name.split())
        
        if len(name) < 3:
            raise ValidationError('Name must be at least 3 characters long.')
        
        return name
    
    def clean_order(self):
        """Ensure order is not negative"""
        order = self.cleaned_data.get('order', 0)
        if order < 0:
            raise ValidationError('Order must be 0 or positive.')
        return order
    
    def clean(self):
        """Validate the form as a whole"""
        cleaned_data = super().clean()
        visibility = cleaned_data.get('visibility')
        main_project = cleaned_data.get('main_project')
        
        # Restricted intros must have a main project
        if visibility == 'restricted' and not main_project:
            raise ValidationError({
                'main_project': 'Restricted intros must have a main project specified.'
            })
        
        return cleaned_data


class IntroLinkForm(forms.ModelForm):
    """Form for linking existing intros to entities"""
    
    intro = forms.ModelChoiceField(
        queryset=Intro.objects.none(),  # Will be set in __init__
        widget=forms.Select(attrs={
            'class': 'form-control browser-default'
        }),
        help_text="Select an existing introduction to link"
    )
    
    class Meta:
        model = IntroRelation
        fields = ['intro', 'status', 'order', 'note']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control browser-default'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control materialize-textarea',
                'rows': 3,
                'placeholder': 'Optional note about this relationship...'
            }),
        }
        help_texts = {
            'status': 'Relationship status - draft relationships are only visible to project admins/moderators',
            'order': 'Display order within the entity (higher numbers appear first)',
            'note': 'Optional note explaining why this intro is relevant to this entity',
        }
    
    def __init__(self, *args, **kwargs):
        self.entity_type = kwargs.pop('entity_type', None)
        self.entity_id = kwargs.pop('entity_id', None)
        self.available_intros = kwargs.pop('available_intros', Intro.objects.none())
        super().__init__(*args, **kwargs)
        
        # Set the intro queryset to available intros
        self.fields['intro'].queryset = self.available_intros
        
        # If no intros available, show helpful message
        if not self.available_intros.exists():
            self.fields['intro'].empty_label = "No suitable intros found"
            self.fields['intro'].help_text = (
                "No intros found that can be linked to this entity. "
                "Intros must have the same main project to be linkable."
            )
        else:
            self.fields['intro'].empty_label = "Select an intro to link"
    
    def clean_order(self):
        """Ensure order is not negative"""
        order = self.cleaned_data.get('order', 0)
        if order < 0:
            raise ValidationError('Order must be 0 or positive.')
        return order


class IntroStatusForm(forms.ModelForm):
    """Form for changing just the status of an intro"""
    
    class Meta:
        model = Intro
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control browser-default'
            }),
        }
        help_texts = {
            'status': 'Only published intros are visible to most users'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Define allowed status transitions
        if self.instance and self.instance.pk:
            current_status = self.instance.status
            
            allowed_transitions = {
                Intro.StatusChoices.DRAFT: [
                    Intro.StatusChoices.DRAFT,
                    Intro.StatusChoices.UNDER_REVIEW,
                    Intro.StatusChoices.PUBLISHED,
                ],
                Intro.StatusChoices.UNDER_REVIEW: [
                    Intro.StatusChoices.UNDER_REVIEW,
                    Intro.StatusChoices.REJECTED,
                    Intro.StatusChoices.PUBLISHED,
                    Intro.StatusChoices.DRAFT,
                ],
                Intro.StatusChoices.REJECTED: [
                    Intro.StatusChoices.REJECTED,
                    Intro.StatusChoices.DRAFT,
                    Intro.StatusChoices.UNDER_REVIEW,
                ],
                Intro.StatusChoices.PUBLISHED: [
                    Intro.StatusChoices.PUBLISHED,
                    Intro.StatusChoices.ARCHIVED,
                    Intro.StatusChoices.UNDER_REVIEW,
                ],
                Intro.StatusChoices.ARCHIVED: [
                    Intro.StatusChoices.ARCHIVED,
                    Intro.StatusChoices.PUBLISHED,
                ],
            }
            
            # Filter choices based on allowed transitions
            allowed = allowed_transitions.get(current_status, Intro.StatusChoices.choices)
            if isinstance(allowed[0], tuple):
                self.fields['status'].choices = allowed
            else:
                all_choices = dict(Intro.StatusChoices.choices)
                self.fields['status'].choices = [
                    (status, all_choices[status]) for status in allowed
                ]


class RelationStatusForm(forms.ModelForm):
    """Form for changing relationship status"""
    
    class Meta:
        model = IntroRelation
        fields = ['status', 'note']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control browser-default'
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control materialize-textarea',
                'rows': 3,
                'placeholder': 'Optional note about this status change...'
            }),
        }
        help_texts = {
            'status': 'Draft relationships are only visible to project admins/moderators',
            'note': 'Optional note about this relationship or status change',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # All relationship status transitions are allowed for now
        # Could add restrictions here if needed in the future


class IntroSearchForm(forms.Form):
    """Form for searching intros"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search intros by name or summary...'
        })
    )
    
    project = forms.ModelChoiceField(
        queryset=None,  # Set in __init__
        required=False,
        empty_label="All projects",
        widget=forms.Select(attrs={
            'class': 'form-control browser-default'
        })
    )
    
    intro_type = forms.ChoiceField(
        choices=[('', 'All types')] + list(Intro.TypeChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control browser-default'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All statuses')] + list(Intro.StatusChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control browser-default'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set project queryset based on user permissions
        if user and user.is_authenticated:
            from project.models import Project, Membership
            user_projects = Project.objects.filter(
                Q(created_by=user) |
                Q(membership__user=user)
            ).distinct()
            self.fields['project'].queryset = user_projects
        else:
            self.fields['project'].queryset = Project.objects.none()