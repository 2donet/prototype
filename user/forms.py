from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from .models import UserProfile
import re
from PIL import Image
import os


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
    

class EditProfileForm(forms.ModelForm):
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
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'validate',
            'id': 'first_name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'validate',
            'id': 'last_name'
        })
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'materialize-textarea validate',
            'id': 'bio',
            'rows': 4
        })
    )
    location = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'validate',
            'id': 'location'
        })
    )
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'validate',
            'id': 'website'
        })
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'avatar-upload-input',
            'id': 'avatar',
            'accept': 'image/jpeg,image/jpg,image/png,image/webp'
        }),
        help_text="Upload a profile picture. Will be automatically resized to 400x400px and converted to WebP format."
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        self.user_profile = kwargs.pop('user_profile', None)
        super().__init__(*args, **kwargs)
        
        # Pre-populate profile fields if profile exists
        if self.user_profile:
            self.fields['bio'].initial = self.user_profile.bio
            self.fields['location'].initial = self.user_profile.location
            self.fields['website'].initial = self.user_profile.website
            self.fields['avatar'].initial = self.user_profile.avatar

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if email is taken by another user
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Check if username is taken by another user
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        
        if avatar:
            # Check file size (5MB limit for upload, but we'll process it down)
            if avatar.size > 5 * 1024 * 1024:
                raise ValidationError("Image file too large (max 5MB).")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if hasattr(avatar, 'content_type') and avatar.content_type not in allowed_types:
                raise ValidationError("Unsupported image format. Please use JPEG, PNG, or WebP.")
            
            # Validate image integrity and minimum size
            try:
                # Open and verify the image
                img = Image.open(avatar)
                img.verify()
                
                # Reset file pointer after verify()
                avatar.seek(0)
                
                # Check minimum dimensions
                img = Image.open(avatar)
                width, height = img.size
                if width < 100 or height < 100:
                    raise ValidationError("Image too small. Minimum size is 100x100 pixels.")
                
                # Check for extremely large dimensions (memory protection)
                if width > 5000 or height > 5000:
                    raise ValidationError("Image dimensions too large. Maximum size is 5000x5000 pixels.")
                
                # Reset file pointer again
                avatar.seek(0)
                
            except Exception as e:
                raise ValidationError("Invalid image file. Please upload a valid image.")
        
        return avatar

    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # Update or create user profile
            if self.user_profile:
                profile = self.user_profile
            else:
                profile, created = UserProfile.objects.get_or_create(user=user)
            
            profile.bio = self.cleaned_data.get('bio', '')
            profile.location = self.cleaned_data.get('location', '')
            profile.website = self.cleaned_data.get('website', '')
            
            # Handle avatar upload
            avatar = self.cleaned_data.get('avatar')
            if avatar:
                # Delete old avatar if it exists (ProcessedImageField will handle this automatically)
                if profile.avatar:
                    # Store old avatar path for cleanup
                    old_avatar_path = profile.avatar.path if profile.avatar else None
                    
                    # Set new avatar (ProcessedImageField will process it automatically)
                    profile.avatar = avatar
                    profile.save()
                    
                    # Clean up old avatar file if it exists
                    if old_avatar_path and os.path.exists(old_avatar_path):
                        try:
                            os.remove(old_avatar_path)
                        except:
                            pass  # Ignore cleanup errors
                else:
                    profile.avatar = avatar
                    profile.save()
            else:
                profile.save()
            
        return user
 


    # Update your EditProfileForm in user/forms.py

