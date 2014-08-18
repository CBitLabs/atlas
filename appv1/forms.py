from django import forms
from django.contrib.auth import authenticate, login

class LoginForm(forms.Form):
        #defining a form class with user name and password fields
    username = forms.CharField(max_length=255, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

        #overriding the clean method
    def clean(self):
        cleaned_data = super(LoginForm, self).clean();
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        if not user or not user.is_active:
            raise forms.ValidationError("Invalid credentials!!! Please try again.")
        return cleaned_data
