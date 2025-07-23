from django import forms
from .models import Message


class MessageForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'materialize-textarea validate',
            'id': 'message_content',
            'placeholder': 'Type your message...',
            'rows': 3,
            'maxlength': 1000,
        }),
        max_length=1000,
        help_text="Maximum 1000 characters"
    )
    
    class Meta:
        model = Message
        fields = ['content']
    
    def clean_content(self):
        content = self.cleaned_data.get('content')
        if not content or not content.strip():
            raise forms.ValidationError("Message cannot be empty.")
        
        # Remove excessive whitespace but preserve intentional line breaks
        content = content.strip()
        if len(content) < 1:
            raise forms.ValidationError("Message cannot be empty.")
        
        return content


class StartConversationForm(forms.Form):
    recipient_username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'validate',
            'id': 'recipient_username',
            'placeholder': 'Enter username...'
        }),
        help_text="Username of the person you want to message"
    )
    
    initial_message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'materialize-textarea validate',
            'id': 'initial_message',
            'placeholder': 'Type your message...',
            'rows': 3,
            'maxlength': 1000,
        }),
        max_length=1000,
        help_text="Your first message"
    )
    
    def clean_recipient_username(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        username = self.cleaned_data.get('recipient_username')
        if not username:
            raise forms.ValidationError("Username is required.")
        
        try:
            user = User.objects.get(username=username)
            return user
        except User.DoesNotExist:
            raise forms.ValidationError(f"User '{username}' does not exist.")
    
    def clean_initial_message(self):
        message = self.cleaned_data.get('initial_message')
        if not message or not message.strip():
            raise forms.ValidationError("Initial message cannot be empty.")
        return message.strip()