from decimal import Decimal
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import (
    Admin,
    Student,
    Instructor,
    UserProfile,
    PasswordResetOTP,
    Course,
    Cart,
    Payment,
    Enrollment,
    CourseContent,
    InstructorMessage,
)

class StudentAccountStatusFilter(admin.SimpleListFilter):
    title = "Account Status"
    parameter_name = "account_status"

    def lookups(self, request, model_admin):
        return [
            ("active", "Active User Account"),
            ("deactivated", "Deactivated User Account"),
            ("unlinked", "No Linked Auth User"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "active":
            active_emails = User.objects.filter(is_active=True).values_list("email", flat=True)
            return queryset.filter(email__in=active_emails)
        elif self.value() == "deactivated":
            inactive_emails = User.objects.filter(is_active=False).values_list("email", flat=True)
            return queryset.filter(email__in=inactive_emails)
        elif self.value() == "unlinked":
            existing_emails = User.objects.values_list("email", flat=True)
            return queryset.exclude(email__in=existing_emails)
        return queryset


class StudentEnrollmentFilter(admin.SimpleListFilter):
    title = "Enrollment Status"
    parameter_name = "has_enrollments"

    def lookups(self, request, model_admin):
        return [
            ("enrolled", "Enrolled in 1+ Courses"),
            ("not_enrolled", "No Course Enrollments"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "enrolled":
            return queryset.filter(enrollments__isnull=False).distinct()
        elif self.value() == "not_enrolled":
            return queryset.filter(enrollments__isnull=True)
        return queryset


class InstructorAccountStatusFilter(admin.SimpleListFilter):
    title = "Account Status"
    parameter_name = "faculty_status"

    def lookups(self, request, model_admin):
        return [
            ("active", "Active Faculty Account"),
            ("deactivated", "Deactivated Faculty Account"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "active":
            active_emails = User.objects.filter(is_active=True).values_list("email", flat=True)
            return queryset.filter(email__in=active_emails)
        elif self.value() == "deactivated":
            inactive_emails = User.objects.filter(is_active=False).values_list("email", flat=True)
            return queryset.filter(email__in=inactive_emails)
        return queryset


class CoursePriceTierFilter(admin.SimpleListFilter):
    title = "Price Range"
    parameter_name = "price_tier"

    def lookups(self, request, model_admin):
        return [
            ("free", "Free (₹0.00)"),
            ("under_500", "Under ₹500"),
            ("500_to_1500", "₹500 – ₹1,500"),
            ("above_1500", "Above ₹1,500"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "free":
            return queryset.filter(price=0)
        elif self.value() == "under_500":
            return queryset.filter(price__gt=0, price__lt=500)
        elif self.value() == "500_to_1500":
            return queryset.filter(price__gte=500, price__lte=1500)
        elif self.value() == "above_1500":
            return queryset.filter(price__gt=1500)
        return queryset


class PaymentAmountTierFilter(admin.SimpleListFilter):
    title = "Payment Tier"
    parameter_name = "amount_tier"

    def lookups(self, request, model_admin):
        return [
            ("under_500", "Under ₹500"),
            ("500_to_1500", "₹500 – ₹1,500"),
            ("above_1500", "Above ₹1,500"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "under_500":
            return queryset.filter(amount__lt=500)
        elif self.value() == "500_to_1500":
            return queryset.filter(amount__gte=500, amount__lte=1500)
        elif self.value() == "above_1500":
            return queryset.filter(amount__gt=1500)
        return queryset


@admin.action(description="Activate selected user accounts")
def activate_selected_users(modeladmin, request, queryset):
    emails = [obj.email.lower() for obj in queryset if obj.email]
    updated = User.objects.filter(email__in=emails).update(is_active=True)
    modeladmin.message_user(request, f"{updated} user account(s) activated successfully.")


@admin.action(description="Deactivate selected user accounts")
def deactivate_selected_users(modeladmin, request, queryset):
    emails = [obj.email.lower() for obj in queryset if obj.email]
    updated = User.objects.filter(email__in=emails).exclude(id=request.user.id).update(is_active=False)
    modeladmin.message_user(request, f"{updated} user account(s) deactivated successfully.")


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ("admin_id", "first_name", "last_name", "email", "phone", "created_at")
    list_filter = (("created_at", admin.DateFieldListFilter),)
    search_fields = ("first_name", "last_name", "email", "phone")
    search_help_text = "Search administrators by name, email, or phone number"
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "student_id",
        "photo_preview",
        "full_name",
        "email",
        "phone",
        "is_account_active",
        "enrolled_courses_count",
        "enrollment_date",
    )
    list_filter = (
        StudentAccountStatusFilter,
        StudentEnrollmentFilter,
        ("enrollment_date", admin.DateFieldListFilter),
    )
    search_fields = ("first_name", "last_name", "email", "phone", "address", "bio")
    search_help_text = "Search students by first name, last name, email, phone, address, or bio"
    ordering = ("-student_id",)
    date_hierarchy = "enrollment_date"
    list_per_page = 25
    readonly_fields = ("enrollment_date",)
    actions = [activate_selected_users, deactivate_selected_users]

    @admin.display(description="Photo")
    def photo_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="width:34px; height:34px; border-radius:50%; object-fit:cover;" />',
                obj.profile_picture.url
            )
        return "-"

    @admin.display(boolean=True, ordering="email", description="Account Active")
    def is_account_active(self, obj):
        u = User.objects.filter(email__iexact=obj.email).first()
        return u.is_active if u else None

    @admin.display(ordering="first_name", description="Full Name")
    def full_name(self, obj):
        return obj.full_name


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = (
        "instructor_id",
        "full_name",
        "email",
        "phone",
        "specialization",
        "is_account_active",
        "courses_count",
        "hire_date",
    )
    list_filter = (
        InstructorAccountStatusFilter,
        "specialization",
        ("hire_date", admin.DateFieldListFilter),
    )
    search_fields = ("first_name", "last_name", "email", "phone", "specialization")
    search_help_text = "Search instructors by name, email, phone, or specialization area"
    ordering = ("-instructor_id",)
    date_hierarchy = "hire_date"
    list_per_page = 25
    readonly_fields = ("hire_date",)
    actions = [activate_selected_users, deactivate_selected_users]

    @admin.display(boolean=True, ordering="email", description="Account Active")
    def is_account_active(self, obj):
        u = User.objects.filter(email__iexact=obj.email).first()
        return u.is_active if u else None

    @admin.display(ordering="first_name", description="Full Name")
    def full_name(self, obj):
        return obj.full_name


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "get_email", "get_is_active", "get_date_joined")
    list_filter = (
        "role",
        "user__is_active",
        ("user__date_joined", admin.DateFieldListFilter),
    )
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email")
    search_help_text = "Search user profiles by username, full name, or email"
    ordering = ("-user__date_joined",)
    list_per_page = 25
    list_select_related = ("user",)
    autocomplete_fields = ("user",)

    @admin.display(ordering="user__email", description="Email")
    def get_email(self, obj):
        return obj.user.email

    @admin.display(boolean=True, ordering="user__is_active", description="Active")
    def get_is_active(self, obj):
        return obj.user.is_active

    @admin.display(ordering="user__date_joined", description="Date Joined")
    def get_date_joined(self, obj):
        return obj.user.date_joined


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "otp", "is_verified", "created_at")
    list_filter = ("is_verified", ("created_at", admin.DateFieldListFilter))
    search_fields = ("user__username", "user__email", "otp")
    search_help_text = "Search OTP verification records by username, email, or 6-digit code"
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25
    list_select_related = ("user",)


class CourseContentInline(admin.TabularInline):
    model = CourseContent
    extra = 1
    fields = ("order", "title", "content_type", "duration", "is_free_preview", "video_url", "notes_file")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "course_id",
        "title",
        "category",
        "price",
        "instructor",
        "is_active",
        "created_at",
    )
    list_filter = (
        "category",
        "is_active",
        CoursePriceTierFilter,
        ("instructor", admin.RelatedOnlyFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "title",
        "description",
        "instructor__first_name",
        "instructor__last_name",
        "instructor__email",
    )
    search_help_text = "Search courses by title, description, or instructor name/email"
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25
    list_select_related = ("instructor",)
    autocomplete_fields = ("instructor",)
    inlines = [CourseContentInline]


@admin.register(CourseContent)
class CourseContentAdmin(admin.ModelAdmin):
    list_display = (
        "content_id",
        "course",
        "title",
        "content_type",
        "order",
        "duration",
        "is_free_preview",
        "has_notes",
        "created_at",
    )
    list_filter = (
        "content_type",
        "is_free_preview",
        ("course", admin.RelatedOnlyFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = ("title", "course__title", "description")
    search_help_text = "Search lessons by title, course name, or description"
    ordering = ("course", "order", "content_id")
    date_hierarchy = "created_at"
    list_per_page = 25
    list_select_related = ("course",)
    autocomplete_fields = ("course",)

    @admin.display(boolean=True, description="Notes Attached")
    def has_notes(self, obj):
        return bool(obj.notes_file)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("cart_id", "student", "course", "added_at")
    list_filter = (
        ("added_at", admin.DateFieldListFilter),
        ("course", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        "student__first_name",
        "student__last_name",
        "student__email",
        "course__title",
    )
    search_help_text = "Search cart entries by student name/email or course title"
    ordering = ("-added_at",)
    date_hierarchy = "added_at"
    list_per_page = 25
    list_select_related = ("student", "course")
    autocomplete_fields = ("student", "course")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "payment_id",
        "student",
        "razorpay_order_id",
        "amount",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        PaymentAmountTierFilter,
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "student__first_name",
        "student__last_name",
        "student__email",
        "razorpay_order_id",
        "razorpay_payment_id",
    )
    search_help_text = "Search payments by student name/email or Razorpay Order/Payment ID"
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25
    list_select_related = ("student",)
    autocomplete_fields = ("student",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("enrollment_id", "student", "course", "status", "enrollment_date")
    list_filter = (
        "status",
        ("course", admin.RelatedOnlyFieldListFilter),
        "course__category",
        ("enrollment_date", admin.DateFieldListFilter),
    )
    search_fields = (
        "student__first_name",
        "student__last_name",
        "student__email",
        "course__title",
    )
    search_help_text = "Search enrollments by student name/email or course title"
    ordering = ("-enrollment_date",)
    date_hierarchy = "enrollment_date"
    list_per_page = 25
    list_select_related = ("student", "course")
    autocomplete_fields = ("student", "course")


@admin.register(InstructorMessage)
class InstructorMessageAdmin(admin.ModelAdmin):
    list_display = (
        "message_id",
        "sender_name",
        "sender_email",
        "instructor",
        "course",
        "subject",
        "is_read",
        "is_replied_display",
        "created_at",
    )
    list_filter = (
        "is_read",
        ("instructor", admin.RelatedOnlyFieldListFilter),
        ("course", admin.RelatedOnlyFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "sender_name",
        "sender_email",
        "subject",
        "message",
        "instructor__first_name",
        "instructor__last_name",
        "course__title",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25
    list_select_related = ("instructor", "course", "sender_user")
    readonly_fields = ("created_at", "replied_at")

    @admin.display(boolean=True, description="Replied")
    def is_replied_display(self, obj):
        return obj.is_replied