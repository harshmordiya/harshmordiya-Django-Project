from django import forms
from django.contrib.auth.models import User

from .models import UserProfile, Student, Instructor, Course


class RegistrationForm(forms.Form):

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Choose a unique username",
            "autocomplete": "username",
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-input",
            "placeholder": "name@example.com",
            "autocomplete": "email",
        })
    )

    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Minimum 8 characters",
            "autocomplete": "new-password",
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Re-enter your password",
            "autocomplete": "new-password",
        })
    )

    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-select",
        })
    )

    # Student details
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Your first name",
        })
    )

    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Your last name (optional)",
        })
    )

    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "+91 9876543210",
        })
    )

    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-textarea",
            "placeholder": "Your city or address (optional)",
            "rows": 3,
        })
    )

    specialization = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "e.g. Web Development, Data Science, AI (for Instructors)",
        })
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
            first_name=self.cleaned_data.get("first_name", ""),
            last_name=self.cleaned_data.get("last_name", ""),
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
                last_name=self.cleaned_data.get("last_name", ""),
                email=self.cleaned_data["email"],
                phone=self.cleaned_data["phone"],
                address=self.cleaned_data.get("address", ""),
            )

        # Create Instructor profile automatically
        elif role == "instructor":
            specialization = self.cleaned_data.get("specialization", "").strip() or "General"
            Instructor.objects.get_or_create(
                email=self.cleaned_data["email"],
                defaults={
                    "first_name": self.cleaned_data["first_name"],
                    "last_name": self.cleaned_data.get("last_name", ""),
                    "phone": self.cleaned_data["phone"],
                    "specialization": specialization,
                }
            )

        return user


class CourseForm(forms.ModelForm):
    """
    Form for instructors to create and update their courses.
    Instructor assignment is handled server-side to guarantee security.
    """
    class Meta:
        model = Course
        fields = [
            "title",
            "category",
            "price",
            "duration",
            "description",
            "is_active",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "e.g. Modern Full-Stack Web Development with Django & React",
            }),
            "category": forms.Select(attrs={
                "class": "form-select",
            }),
            "price": forms.NumberInput(attrs={
                "class": "form-input",
                "placeholder": "e.g. 1499.00",
                "step": "0.01",
                "min": "0",
            }),
            "duration": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "e.g. 8 weeks or 30 hours",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 6,
                "placeholder": "Comprehensive overview of the course syllabus, what students will build, and prerequisites...",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-checkbox",
            }),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price < 0:
            raise forms.ValidationError("Course price cannot be negative.")
        return price

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 3:
            raise forms.ValidationError("Course title must be at least 3 characters long.")
        return title
