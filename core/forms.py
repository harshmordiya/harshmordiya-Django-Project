from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class RegistrationForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES
    )

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
        )

        UserProfile.objects.create(
            user=user,
            role=self.cleaned_data["role"]
        )

        return user