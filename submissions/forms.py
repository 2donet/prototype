# forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from skills.models import Skill
from submissions.models import Submission
from project.models import Project
from task.models import Task
from need.models import Need


class SubmissionForm(forms.ModelForm):
    """
    Enhanced form for creating submissions with better validation and UX
    """
    
    class Meta:
        model = Submission
        fields = ['to_project', 'to_task', 'to_need', 'why_fit', 'relevant_skills', 'additional_info']
        widgets = {
            'to_project': forms.Select(attrs={
                'class': 'browser-default',
                'id': 'id_to_project'
            }),
            'to_task': forms.Select(attrs={
                'class': 'browser-default',
                'id': 'id_to_task'
            }),
            'to_need': forms.Select(attrs={
                'class': 'browser-default',
                'id': 'id_to_need'
            }),
            'why_fit': forms.Textarea(attrs={
                'class': 'materialize-textarea',
                'placeholder': 'Explain why you are a good fit for this opportunity. What makes you qualified? (Optional)',
                'rows': 4,
                'maxlength': 1000
            }),
            'relevant_skills': forms.SelectMultiple(attrs={
                'class': 'browser-default',
                'multiple': True,
                'size': 8
            }),
            'additional_info': forms.Textarea(attrs={
                'class': 'materialize-textarea',
                'placeholder': 'Any additional information, links to portfolio, GitHub, LinkedIn, etc. (Optional)',
                'rows': 3,
                'maxlength': 500
            }),
        }
        labels = {
            'to_project': 'Project',
            'to_task': 'Task',
            'to_need': 'Need',
            'why_fit': 'Why are you a good fit? (Optional)',
            'relevant_skills': 'Relevant Skills (Optional)',
            'additional_info': 'Additional Information (Optional)',
        }
        help_texts = {
            'why_fit': 'Briefly describe your interest, qualifications, and what you can bring to this opportunity.',
            'relevant_skills': 'Select skills from the list that are most relevant to this opportunity.',
            'additional_info': 'Provide any additional details, links to your work, or other relevant information.',
        }

    def __init__(self, *args, **kwargs):
        # Allow passing user to filter available options
        self.user = kwargs.pop('user', None)
        # Allow pre-selecting content type and ID
        self.content_type = kwargs.pop('content_type', None)
        self.content_id = kwargs.pop('content_id', None)
        
        super().__init__(*args, **kwargs)
        
        # Make fields optional
        self.fields['why_fit'].required = False
        self.fields['relevant_skills'].required = False
        self.fields['additional_info'].required = False
        
        # Filter querysets to show only active/available items
        try:
            if hasattr(Project, 'is_active'):
                self.fields['to_project'].queryset = Project.objects.filter(is_active=True).order_by('title')
            else:
                self.fields['to_project'].queryset = Project.objects.order_by('title')
        except:
            self.fields['to_project'].queryset = Project.objects.none()
        
        try:
            if hasattr(Task, 'is_active'):
                self.fields['to_task'].queryset = Task.objects.filter(is_active=True).order_by('title')
            else:
                self.fields['to_task'].queryset = Task.objects.order_by('title')
        except:
            self.fields['to_task'].queryset = Task.objects.none()
        
        try:
            if hasattr(Need, 'is_active'):
                self.fields['to_need'].queryset = Need.objects.filter(is_active=True).order_by('title')
            else:
                self.fields['to_need'].queryset = Need.objects.order_by('title')
        except:
            self.fields['to_need'].queryset = Need.objects.none()
        
        # Order skills alphabetically
        try:
            if hasattr(Skill, 'is_active'):
                self.fields['relevant_skills'].queryset = Skill.objects.filter(is_active=True).order_by('name')
            else:
                self.fields['relevant_skills'].queryset = Skill.objects.order_by('name')
        except:
            self.fields['relevant_skills'].queryset = Skill.objects.none()
        
        # Add empty option to select fields
        self.fields['to_project'].empty_label = "Select a project..."
        self.fields['to_task'].empty_label = "Select a task..."
        self.fields['to_need'].empty_label = "Select a need..."
        
        # If user is provided, filter out items they already submitted to
        if self.user:
            try:
                existing_submissions = Submission.objects.filter(applicant=self.user)
                
                # Filter out projects/tasks user already applied to
                submitted_projects = existing_submissions.filter(
                    to_project__isnull=False
                ).values_list('to_project', flat=True)
                
                submitted_tasks = existing_submissions.filter(
                    to_task__isnull=False
                ).values_list('to_task', flat=True)
                
                if submitted_projects:
                    self.fields['to_project'].queryset = self.fields['to_project'].queryset.exclude(
                        id__in=submitted_projects
                    )
                
                if submitted_tasks:
                    self.fields['to_task'].queryset = self.fields['to_task'].queryset.exclude(
                        id__in=submitted_tasks
                    )
            except Exception as e:
                print(f"DEBUG: Error filtering existing submissions: {e}")
        
        # Pre-select content if provided
        if self.content_type and self.content_id:
            if self.content_type == 'project':
                self.fields['to_project'].initial = self.content_id
                # Hide other content type fields
                self.fields['to_task'].widget = forms.HiddenInput()
                self.fields['to_need'].widget = forms.HiddenInput()
            elif self.content_type == 'task':
                self.fields['to_task'].initial = self.content_id
                # Hide other content type fields
                self.fields['to_project'].widget = forms.HiddenInput()
                self.fields['to_need'].widget = forms.HiddenInput()
            elif self.content_type == 'need':
                self.fields['to_need'].initial = self.content_id
                # Hide other content type fields
                self.fields['to_project'].widget = forms.HiddenInput()
                self.fields['to_task'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        to_project = cleaned_data.get('to_project')
        to_task = cleaned_data.get('to_task')
        to_need = cleaned_data.get('to_need')
        
        # Ensure exactly one target is selected
        selected_count = sum(bool(x) for x in [to_project, to_task, to_need])
        
        if selected_count == 0:
            raise ValidationError('Please select either a project, task, or need to apply to.')
        elif selected_count > 1:
            raise ValidationError('Please select only one target (project, task, or need).')
        
        # Check if user already submitted to this content
        if self.user:
            try:
                existing_submission = None
                if to_project:
                    existing_submission = Submission.objects.filter(
                        applicant=self.user, to_project=to_project
                    ).first()
                elif to_task:
                    existing_submission = Submission.objects.filter(
                        applicant=self.user, to_task=to_task
                    ).first()
                # Note: to_need doesn't have unique_together constraint, so multiple submissions allowed
                
                if existing_submission:
                    content_type = 'project' if to_project else 'task'
                    raise ValidationError(f'You have already submitted to this {content_type}.')
            except Exception as e:
                print(f"DEBUG: Error checking existing submissions: {e}")
        
        return cleaned_data

    def save(self, commit=True):
        submission = super().save(commit=False)
        
        # Set the applicant if user is provided
        if self.user:
            submission.applicant = self.user
        
        if commit:
            submission.save()
            self.save_m2m()  # Save many-to-many relationships
        
        return submission


class SubmissionQuickForm(forms.ModelForm):
    """
    Simplified form for quick submissions from specific content pages
    """
    
    class Meta:
        model = Submission
        fields = ['why_fit', 'relevant_skills', 'additional_info']
        widgets = {
            'why_fit': forms.Textarea(attrs={
                'class': 'materialize-textarea',
                'placeholder': 'Why are you interested in this opportunity? (Optional)',
                'rows': 3
            }),
            'relevant_skills': forms.SelectMultiple(attrs={
                'class': 'browser-default',
                'multiple': True,
                'size': 6
            }),
            'additional_info': forms.Textarea(attrs={
                'class': 'materialize-textarea',
                'placeholder': 'Additional information (Optional)',
                'rows': 2
            }),
        }
        labels = {
            'why_fit': 'Why are you a good fit? (Optional)',
            'relevant_skills': 'Your Relevant Skills (Optional)',
            'additional_info': 'Additional Information (Optional)',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.content_object = kwargs.pop('content_object', None)
        
        super().__init__(*args, **kwargs)
        
        print(f"DEBUG: SubmissionQuickForm initialized with user={self.user}, content_object={self.content_object}")
        
        # Make all fields optional
        self.fields['why_fit'].required = False
        self.fields['relevant_skills'].required = False
        self.fields['additional_info'].required = False
        
        # Filter skills
        try:
            if hasattr(Skill, 'is_active'):
                self.fields['relevant_skills'].queryset = Skill.objects.filter(is_active=True).order_by('name')
            else:
                self.fields['relevant_skills'].queryset = Skill.objects.order_by('name')
        except:
            self.fields['relevant_skills'].queryset = Skill.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        print(f"DEBUG: SubmissionQuickForm.clean() called with cleaned_data: {cleaned_data}")
        print(f"DEBUG: self.content_object = {self.content_object}")
        print(f"DEBUG: self.user = {self.user}")
        return cleaned_data

    def save(self, commit=True):
        print(f"DEBUG: SubmissionQuickForm.save() called with commit={commit}")
        submission = super().save(commit=False)
        
        print(f"DEBUG: Created submission object: {submission}")
        print(f"DEBUG: submission.to_project = {submission.to_project}")
        print(f"DEBUG: submission.to_task = {submission.to_task}")
        print(f"DEBUG: submission.to_need = {submission.to_need}")
        
        if self.user:
            submission.applicant = self.user
            print(f"DEBUG: Set applicant to {self.user}")
        
        if self.content_object:
            print(f"DEBUG: Content object type: {type(self.content_object)}")
            print(f"DEBUG: Content object: {self.content_object}")
            
            # Set the appropriate foreign key based on content type
            if isinstance(self.content_object, Project):
                submission.to_project = self.content_object
                print(f"DEBUG: Set to_project = {self.content_object}")
            elif isinstance(self.content_object, Task):
                submission.to_task = self.content_object
                print(f"DEBUG: Set to_task = {self.content_object}")
            elif isinstance(self.content_object, Need):
                submission.to_need = self.content_object
                print(f"DEBUG: Set to_need = {self.content_object}")
            else:
                print(f"DEBUG: WARNING - Unknown content object type: {type(self.content_object)}")
        else:
            print(f"DEBUG: WARNING - No content_object provided!")
        
        print(f"DEBUG: Final submission state before save:")
        print(f"DEBUG: - applicant: {submission.applicant}")
        print(f"DEBUG: - to_project: {submission.to_project}")
        print(f"DEBUG: - to_task: {submission.to_task}")
        print(f"DEBUG: - to_need: {submission.to_need}")
        print(f"DEBUG: - why_fit: {submission.why_fit}")
        
        if commit:
            # Validate before saving
            try:
                submission.full_clean()
                print(f"DEBUG: Submission validation passed")
                submission.save()
                print(f"DEBUG: Submission saved successfully with ID: {submission.id}")
                self.save_m2m()
                print(f"DEBUG: Many-to-many relationships saved")
            except Exception as e:
                print(f"DEBUG: Error during submission save: {e}")
                raise
        
        return submission

    def save(self, commit=True):
        submission = super().save(commit=False)
        
        if self.user:
            submission.applicant = self.user
        
        if self.content_object:
            # Set the appropriate foreign key based on content type
            if isinstance(self.content_object, Project):
                submission.to_project = self.content_object
            elif isinstance(self.content_object, Task):
                submission.to_task = self.content_object
            elif isinstance(self.content_object, Need):
                submission.to_need = self.content_object
        
        if commit:
            submission.save()
            self.save_m2m()
        
        return submission


class SubmissionFilterForm(forms.Form):
    """
    Form for filtering submissions in the admin/list views
    """
    
    STATUS_CHOICES = [('', 'All Statuses')] + Submission.STATUS_CHOICES
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'browser-default'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'browser-default',
            'placeholder': 'Search applicants...'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'datepicker',
            'placeholder': 'From date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'datepicker',
            'placeholder': 'To date'
        })
    )
    
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'browser-default',
            'multiple': True,
            'size': 6
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            if hasattr(Skill, 'is_active'):
                self.fields['skills'].queryset = Skill.objects.filter(is_active=True).order_by('name')
            else:
                self.fields['skills'].queryset = Skill.objects.order_by('name')
        except:
            self.fields['skills'].queryset = Skill.objects.none()


class SubmissionStatusUpdateForm(forms.ModelForm):
    """
    Form for updating submission status (for admins/reviewers)
    """
    
    class Meta:
        model = Submission
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'browser-default'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].required = True