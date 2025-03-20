from django import forms

class LoginForm(forms.Form):
    email = forms.EmailField(label='Email', required=True)
    password = forms.CharField(label='Password', widget=forms.PasswordInput, required=True)
    remember_me = forms.BooleanField(label='Remember Me', required=False)

class RegistrationForm(forms.Form):
    username = forms.CharField(label='Username', min_length=3, max_length=64, required=True)
    email = forms.EmailField(label='Email', required=True)
    password = forms.CharField(label='Password', widget=forms.PasswordInput, min_length=6, required=True)

class ResetPasswordRequestForm(forms.Form):
    email = forms.EmailField(label='Email', required=True)

class ResetPasswordForm(forms.Form):
    password = forms.CharField(label='New Password', widget=forms.PasswordInput, min_length=6, required=True)

class GameResponseForm(forms.Form):
    choice = forms.CharField(label='Your Response', widget=forms.Textarea, required=True)