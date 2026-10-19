import os
from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from .models import UserProfile, Student, Instructor, Course, CourseContent, InstructorMessage
from .validators import validate_course_notes_file


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
            Student.objects.get_or_create(
                email=self.cleaned_data["email"],
                defaults={
                    "first_name": self.cleaned_data["first_name"],
                    "last_name": self.cleaned_data.get("last_name", ""),
                    "phone": self.cleaned_data["phone"],
                    "address": self.cleaned_data.get("address", ""),
                    "enrollment_date": timezone.now(),
                }
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


class CourseContentForm(forms.ModelForm):
    class Meta:
        model = CourseContent
        fields = [
            "title",
            "content_type",
            "order",
            "duration",
            "is_free_preview",
            "video_url",
            "notes_file",
            "file_url",
            "description",
            "text_content",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control form-input",
                "placeholder": "e.g. Lesson 1: Introduction & Setup",
            }),
            "content_type": forms.Select(attrs={
                "class": "form-select",
            }),
            "order": forms.NumberInput(attrs={
                "class": "form-control form-input",
                "min": "1",
                "placeholder": "1",
            }),
            "duration": forms.TextInput(attrs={
                "class": "form-control form-input",
                "placeholder": "e.g. 15 mins",
            }),
            "is_free_preview": forms.CheckboxInput(attrs={
                "class": "form-check-input form-checkbox",
            }),
            "video_url": forms.URLInput(attrs={
                "class": "form-control form-input",
                "placeholder": "https://www.youtube.com/watch?v=... or Vimeo / lecture link",
            }),
            "notes_file": forms.ClearableFileInput(attrs={
                "class": "form-control form-input",
                "accept": ".pdf,.docx,.txt,.pptx",
            }),
            "file_url": forms.URLInput(attrs={
                "class": "form-control form-input",
                "placeholder": "https://... link to external study notes, slides, or PDF",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control form-textarea",
                "rows": 3,
                "placeholder": "Brief summary of what this lesson covers...",
            }),
            "text_content": forms.Textarea(attrs={
                "class": "form-control form-textarea",
                "rows": 6,
                "placeholder": "Full lecture notes, code snippets, or reading text...",
            }),
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 2:
            raise forms.ValidationError("Content title must be at least 2 characters long.")
        return title

    def clean_notes_file(self):
        file = self.cleaned_data.get("notes_file")
        if file:
            validate_course_notes_file(file)
        return file


# Aliases for explicit notes/video upload forms
CourseNotesAndVideoForm = CourseContentForm
CourseMaterialUploadForm = CourseContentForm


class StudentProfileForm(forms.ModelForm):
    """
    Form for students to view and update their personal profile details.
    Synchronizes first name, last name, and email with the underlying User account.
    Supports profile picture upload with real-time preview and removal.
    """
    clear_profile_picture = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput(attrs={"id": "id_clear_profile_picture"}),
        help_text="Remove existing profile picture",
    )

    class Meta:
        model = Student
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
            "address",
            "bio",
            "profile_picture",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Your first name",
                "required": True,
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Your last name (optional)",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-input",
                "placeholder": "name@example.com",
                "required": True,
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "+91 9876543210",
            }),
            "date_of_birth": forms.DateInput(attrs={
                "class": "form-input",
                "type": "date",
            }),
            "address": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 3,
                "placeholder": "City, State, Country (optional)",
            }),
            "bio": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 4,
                "placeholder": "Tell us about your learning goals, skills, and background...",
            }),
            "profile_picture": forms.FileInput(attrs={
                "class": "form-file-input",
                "accept": "image/jpeg,image/png,image/webp,image/gif",
                "id": "id_profile_picture",
            }),
        }
        error_messages = {
            "profile_picture": {
                "invalid_image": "The uploaded file is not a valid image. Please select a valid image file.",
            }
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_first_name(self):
        first_name = self.cleaned_data.get("first_name", "").strip()
        if not first_name:
            raise forms.ValidationError("First name is required.")
        return first_name

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise forms.ValidationError("Email address is required.")

        # Ensure no collision with other users
        user_qs = User.objects.filter(email__iexact=email)
        if self.user:
            user_qs = user_qs.exclude(id=self.user.id)
        if user_qs.exists():
            raise forms.ValidationError("This email is already associated with another account.")

        student_qs = Student.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            student_qs = student_qs.exclude(pk=self.instance.pk)
        if student_qs.exists():
            raise forms.ValidationError("Another student record already exists with this email address.")

        return email

    def clean_profile_picture(self):
        picture = self.cleaned_data.get("profile_picture")
        if not picture:
            return picture

        if hasattr(picture, "size"):
            max_size_mb = 5
            if picture.size > max_size_mb * 1024 * 1024:
                raise forms.ValidationError(f"Profile picture file size must be under {max_size_mb} MB.")

            from PIL import Image
            try:
                img = Image.open(picture)
                img.verify()
                allowed_formats = {"JPEG", "JPG", "PNG", "WEBP", "GIF"}
                if img.format and img.format.upper() not in allowed_formats:
                    raise forms.ValidationError(
                        f"Unsupported format ({img.format}). Please upload a JPEG, PNG, WEBP, or GIF image."
                    )
                if hasattr(picture, "seek"):
                    picture.seek(0)
            except forms.ValidationError:
                raise
            except Exception:
                raise forms.ValidationError("The uploaded file is not a valid image. Please select a JPEG, PNG, WEBP, or GIF file.")

        return picture

    def save(self, commit=True):
        student = super().save(commit=False)

        # Handle removing profile picture if requested
        if self.cleaned_data.get("clear_profile_picture"):
            if student.profile_picture:
                try:
                    student.profile_picture.delete(save=False)
                except Exception:
                    pass
                student.profile_picture = None

        if commit:
            student.save()
            self.save_m2m()

        # Synchronize first_name, last_name, and email to auth.User
        if self.user:
            self.user.first_name = self.cleaned_data.get("first_name", "").strip()
            self.user.last_name = self.cleaned_data.get("last_name", "").strip()
            self.user.email = self.cleaned_data.get("email", "").strip().lower()
            if commit:
                self.user.save(update_fields=["first_name", "last_name", "email"])
        return student


class ContactInstructorForm(forms.ModelForm):
    """
    Form allowing students and site visitors to contact a course instructor
    with a direct message or inquiry.
    """
    class Meta:
        model = InstructorMessage
        fields = [
            "sender_name",
            "sender_email",
            "course",
            "subject",
            "message",
        ]
        widgets = {
            "sender_name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Your full name",
                "required": True,
            }),
            "sender_email": forms.EmailInput(attrs={
                "class": "form-input",
                "placeholder": "your.email@example.com",
                "required": True,
            }),
            "course": forms.Select(attrs={
                "class": "form-select",
            }),
            "subject": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "e.g., Question about course prerequisites or assignments",
                "required": True,
            }),
            "message": forms.Textarea(attrs={
                "class": "form-textarea",
                "rows": 6,
                "placeholder": "Type your message or inquiry for the instructor here...",
                "required": True,
            }),
        }

    def __init__(self, *args, instructor=None, user=None, initial_course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instructor = instructor
        self.user = user

        # Filter the course dropdown to courses taught by this instructor
        if instructor:
            self.fields["course"].queryset = Course.objects.filter(instructor=instructor).order_by("title")
            self.fields["course"].empty_label = "-- General Inquiry (No specific course) --"
            self.fields["course"].required = False
        else:
            self.fields["course"].queryset = Course.objects.none()

        if initial_course:
            self.fields["course"].initial = initial_course

        # Auto-fill from authenticated user session
        if user and user.is_authenticated:
            full_name = f"{user.first_name} {user.last_name}".strip() or user.username
            if not self.initial.get("sender_name"):
                self.initial["sender_name"] = full_name
            if not self.initial.get("sender_email") and user.email:
                self.initial["sender_email"] = user.email

    def clean_sender_name(self):
        name = self.cleaned_data.get("sender_name", "").strip()
        if not name:
            raise forms.ValidationError("Please provide your name.")
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters long.")
        return name

    def clean_subject(self):
        subject = self.cleaned_data.get("subject", "").strip()
        if not subject:
            raise forms.ValidationError("Subject is required.")
        if len(subject) < 3:
            raise forms.ValidationError("Subject must be at least 3 characters long.")
        return subject

    def clean_message(self):
        message = self.cleaned_data.get("message", "").strip()
        if not message:
            raise forms.ValidationError("Please enter your message.")
        if len(message) < 10:
            raise forms.ValidationError("Message must be at least 10 characters long.")
        return message


class InstructorReplyForm(forms.Form):
    """
    Form for instructors to submit a direct reply to a student message.
    """
    reply_text = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-textarea",
            "rows": 5,
            "placeholder": "Type your response to the student here...",
            "required": True,
        }),
        help_text="Your reply will be recorded in the system and emailed to the student."
    )

    def clean_reply_text(self):
        text = self.cleaned_data.get("reply_text", "").strip()
        if not text:
            raise forms.ValidationError("Reply cannot be empty.")
        if len(text) < 5:
            raise forms.ValidationError("Please provide a more descriptive reply (at least 5 characters).")
        return text



