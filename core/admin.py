from django.contrib import admin

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
)

@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ("admin_id", "first_name", "last_name", "email", "phone", "created_at")
    search_fields = ("first_name", "last_name", "email")

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "first_name", "last_name", "email", "phone", "enrollment_date")
    search_fields = ("first_name", "last_name", "email")

@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ("instructor_id", "first_name", "last_name", "email", "specialization")
    search_fields = ("first_name", "last_name", "email", "specialization")

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")

@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "otp", "created_at", "is_verified")
    list_filter = ("is_verified", "created_at")
    search_fields = ("user__username", "user__email", "otp")

class CourseContentInline(admin.TabularInline):
    model = CourseContent
    extra = 1
    fields = ("order", "title", "content_type", "duration", "is_free_preview", "video_url")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("course_id", "title", "category", "price", "instructor", "is_active", "created_at")
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("title", "description")
    inlines = [CourseContentInline]


@admin.register(CourseContent)
class CourseContentAdmin(admin.ModelAdmin):
    list_display = ("content_id", "course", "title", "content_type", "order", "duration", "is_free_preview", "created_at")
    list_filter = ("content_type", "is_free_preview", "created_at")
    search_fields = ("title", "course__title", "description")
    ordering = ("course", "order", "content_id")

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("cart_id", "student", "course", "added_at")
    list_filter = ("added_at",)
    search_fields = ("student__first_name", "student__last_name", "student__email", "course__title")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "student", "razorpay_order_id", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("student__email", "razorpay_order_id", "razorpay_payment_id")

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("enrollment_id", "student", "course", "status", "enrollment_date")
    list_filter = ("status", "enrollment_date")
    search_fields = ("student__email", "course__title")