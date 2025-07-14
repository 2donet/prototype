# forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
import re

class SignInForm(AuthenticationForm):
    username = forms.CharField(
        max_length=254, 
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'class': 'validate',
            'id': 'username'
        })
    )
    password = forms.CharField(
        label="Password", 
        widget=forms.PasswordInput(attrs={
            'class': 'validate',
            'id': 'password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'tooltipped not-available',
            'data-position': 'top',
            'data-tooltip': 'Remember me functionality not available yet',
            'disabled': True
        })
    )

class SignupForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'validate',
            'id': 'username'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'validate',
            'id': 'email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'validate',
            'id': 'password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'validate',
            'id': 'confirm_password'
        })
    )
    agree_terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the Terms & Conditions'},
        widget=forms.CheckboxInput(attrs={
            'id': 'agree_terms'
        })
    )
    agree_privacy = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must read and agree to the Privacy Policy'},
        widget=forms.CheckboxInput(attrs={
            'id': 'agree_privacy'
        })
    )
    newsletter = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'id': 'newsletter'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        
        # Password validation
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter.")
        
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least one number.")
        
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        agree_terms = cleaned_data.get('agree_terms')
        agree_privacy = cleaned_data.get('agree_privacy')

        # Check password confirmation
        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError("Passwords do not match.")

        # Check required agreements
        if not agree_terms:
            raise ValidationError("You must agree to the Terms & Conditions.")
        
        if not agree_privacy:
            raise ValidationError("You must read and agree to the Privacy Policy.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])
        
        if commit:
            user.save()
            
            # Create user profile
            from .models import UserProfile
            UserProfile.objects.create(user=user)
            
            # Add to Normal group if it exists
            try:
                normal_group = Group.objects.get(name='Normal')
                normal_group.user_set.add(user)
            except Group.DoesNotExist:
                pass  # Group doesn't exist, that's okay
            
            # Store newsletter preference (you might want to create a model for this)
            # For now, we'll just pass it through
            user.newsletter_opt_in = self.cleaned_data.get('newsletter', False)
            
        return user