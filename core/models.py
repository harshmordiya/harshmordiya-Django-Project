from decimal import Decimal
from django.db import models
from django.utils import timezone


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
    last_name = models.CharField(max_length=100, blank=True, default="")
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True, default="")
    address = models.TextField(blank=True, default="")
    enrollment_date = models.DateTimeField(default=timezone.now, null=True, blank=True)

    class Meta:
        ordering = ["-student_id"]
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.email

    @property
    def full_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.email

    @property
    def enrolled_courses_count(self):
        if "enrolled_courses_count" in self.__dict__:
            return self.__dict__["enrolled_courses_count"]
        return self.enrollments.filter(status__in=["active", "completed"]).count()

    @enrolled_courses_count.setter
    def enrolled_courses_count(self, value):
        self.__dict__["enrolled_courses_count"] = value

    @property
    def enrollments_count(self):
        if "enrollments_count" in self.__dict__:
            return self.__dict__["enrollments_count"]
        return self.enrolled_courses_count

    @enrollments_count.setter
    def enrollments_count(self, value):
        self.__dict__["enrollments_count"] = value

    @property
    def total_paid_amount(self):
        if "total_paid_amount" in self.__dict__:
            return self.__dict__["total_paid_amount"]
        total = self.payments.filter(status__iexact="paid").aggregate(models.Sum("amount"))["amount__sum"]
        return total or Decimal("0.00")

    @total_paid_amount.setter
    def total_paid_amount(self, value):
        self.__dict__["total_paid_amount"] = value

    @property
    def paid_total(self):
        if "paid_total" in self.__dict__:
            return self.__dict__["paid_total"]
        return self.total_paid_amount

    @paid_total.setter
    def paid_total(self, value):
        self.__dict__["paid_total"] = value


class Instructor(models.Model):
    instructor_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, default="")
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, default="")
    specialization = models.CharField(max_length=150, blank=True, default="General")
    hire_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-instructor_id"]
        verbose_name = "Instructor"
        verbose_name_plural = "Instructors"

    def __str__(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.email

    @property
    def full_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.email

    @property
    def courses(self):
        return self.course_set.all()

    @property
    def courses_count(self):
        if "courses_count" in self.__dict__:
            return self.__dict__["courses_count"]
        return self.course_set.count()

    @courses_count.setter
    def courses_count(self, value):
        self.__dict__["courses_count"] = value

    @property
    def students_count(self):
        if "students_count" in self.__dict__:
            return self.__dict__["students_count"]
        return self.course_set.filter(
            enrollments__status__in=["active", "completed"]
        ).values("enrollments__student").distinct().count()

    @students_count.setter
    def students_count(self, value):
        self.__dict__["students_count"] = value


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

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_verified = models.BooleanField(
        default=False
    )

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

    title = models.CharField(
        max_length=200
    )

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    description = models.TextField()

    duration = models.CharField(
        max_length=100
    )

    instructor = models.ForeignKey(
        "Instructor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    enrollment_id = models.AutoField(primary_key=True)

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    enrollment_date = models.DateTimeField(
        auto_now_add=True
    )

    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment"
            )
        ]

    def __str__(self):
        return f"{self.student} - {self.course} ({self.status})"
    
class Cart(models.Model):
    cart_id = models.AutoField(
        primary_key=True
    )

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

    added_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_cart"
            )
        ]

    def __str__(self):
        return f"{self.student} - {self.course}"


class Payment(models.Model):
    payment_id = models.AutoField(
        primary_key=True
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    razorpay_order_id = models.CharField(
        max_length=100,
        unique=True
    )

    razorpay_payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    razorpay_signature = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=30,
        default="created"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.student} - {self.razorpay_order_id}"


class CourseContent(models.Model):
    CONTENT_TYPE_CHOICES = [
        ("video", "Video Lesson"),
        ("document", "Document / PDF"),
        ("article", "Reading / Article"),
        ("quiz", "Quiz / Exercise"),
        ("assignment", "Assignment"),
        ("other", "Other"),
    ]

    content_id = models.AutoField(
        primary_key=True
    )
    
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="contents"
    )

    title = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    content_type = models.CharField(
        max_length=30,
        choices=CONTENT_TYPE_CHOICES,
        default="video"
    )

    video_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Link to lecture video (YouTube, Vimeo, or external stream)"
    )

    notes_file = models.FileField(
        upload_to="course_notes/",
        blank=True,
        null=True,
        help_text="Upload notes document directly (PDF, DOCX, TXT, PPT, etc.)"
    )

    file_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Link to external study material, PDF, or resource"
    )

    text_content = models.TextField(
        blank=True,
        null=True,
        help_text="Lesson notes, article text, or lecture transcript"
    )

    order = models.PositiveIntegerField(
        default=1,
        help_text="Display order in course syllabus"
    )

    duration = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Estimated duration (e.g. 15 mins)"
    )

    is_free_preview = models.BooleanField(
        default=False,
        help_text="Whether this content is visible before purchasing"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["order", "content_id"]
        verbose_name = "Course Content"
        verbose_name_plural = "Course Contents"

    def __str__(self):
        return f"{self.course.title} - {self.title}"
