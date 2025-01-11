# forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm

class SignInForm(AuthenticationForm):
    username = forms.CharField(max_length=254, widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
