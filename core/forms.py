from django import forms
from django.contrib.auth.models import User

from .models import UserProfile, Student


class RegistrationForm(forms.Form):

    username = forms.CharField(
        max_length=150
    )

    email = forms.EmailField()

    password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=8
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput
    )

    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES
    )

    # Student details
    first_name = forms.CharField(
        max_length=100
    )

    last_name = forms.CharField(
        max_length=100,
        required=False
    )

    phone = forms.CharField(
        max_length=15
    )

    address = forms.CharField(
        widget=forms.Textarea,
        required=False
    )

    def clean_username(self):

        username = self.cleaned_data["username"]

        if User.objects.filter(
            username=username
        ).exists():

            raise forms.ValidationError(
                "This username is already registered."
            )

        return username

    def clean_email(self):

        email = self.cleaned_data["email"]

        if User.objects.filter(
            email=email
        ).exists():

            raise forms.ValidationError(
                "This email is already registered."
            )

        return email

    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get(
            "confirm_password"
        )

        if password and confirm_password:

            if password != confirm_password:

                raise forms.ValidationError(
                    "Passwords do not match."
                )

        return cleaned_data

    def save(self):

        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
        )

        role = self.cleaned_data["role"]

        # Create UserProfile
        UserProfile.objects.create(
            user=user,
            role=role
        )

        # Create Student profile automatically
        if role == "student":

            Student.objects.create(
                first_name=self.cleaned_data["first_name"],
                last_name=self.cleaned_data["last_name"],
                email=self.cleaned_data["email"],
                phone=self.cleaned_data["phone"],
                address=self.cleaned_data["address"],
            )

        return user