# forms.py
from django import forms
from django.contrib.auth.models import User, Group

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            # Optionally add the user to the 'Normal' group
            
            normal_group = Group.objects.get(name='Normal')
            normal_group.user_set.add(user)
        return user
