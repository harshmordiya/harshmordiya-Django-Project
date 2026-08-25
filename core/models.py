from django.db import models


class Admin(models.Model):
    admin_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    enrollment_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Instructor(models.Model):
    instructor_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    specialization = models.CharField(max_length=150)
    hire_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("student", "Student"),
        ("instructor", "Instructor"),
    ]

    user = models.OneToOneField(
        "auth.User",
        on_delete=models.CASCADE
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE
    )
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.otp}"


class Course(models.Model):
    CATEGORY_CHOICES = [
        ("programming", "Programming"),
        ("web_development", "Web Development"),
        ("data_science", "Data Science"),
        ("design", "Design"),
        ("business", "Business"),
        ("other", "Other"),
    ]

    course_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    description = models.TextField()
    duration = models.CharField(max_length=100)
    instructor = models.ForeignKey(
        "Instructor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class Cart(models.Model):
    cart_id = models.AutoField(primary_key=True)

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_cart"
            )
        ]

    def __str__(self):
        return f"{self.student} - {self.course}"