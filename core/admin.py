from django.contrib import admin

# Register your models here.
from .models import (
    Admin,
    Student,
    Instructor,
    UserProfile,
    PasswordResetOTP,
    Course,
    Cart,
)

admin.site.register(Admin)
admin.site.register(Student)
admin.site.register(Instructor)
admin.site.register(UserProfile)
admin.site.register(PasswordResetOTP)
admin.site.register(Course)
admin.site.register(Cart)

class AdminAdmin(admin.ModelAdmin):
    list_display = (
        "admin_id","first_name","last_name","email","phone","created_at",
    )

    search_fields = (
        "first_name","last_name","email",
    )

class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id","first_name","last_name","email","phone","enrollment_date",
    )

    search_fields = ("first_name","last_name","email",
    )

class InstructorAdmin(admin.ModelAdmin):
    list_display = ("instructor_id","first_name","last_name","email","specialization",
    )

    search_fields = (
        "first_name", "last_name", "email", "specialization",
    )

class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user","role",
    )

    list_filter = (
        "role",
    )

    search_fields = (
        "user__username","user__email",
    )

class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = (
        "user","otp","created_at","is_verified",
    )

    list_filter = (
        "is_verified","created_at",
    )

    search_fields = (
        "user__username","user__email","otp",
    )

class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "course_id","title","category","price","instructor","is_active","created_at",
    )

    list_filter = (
        "category", "is_active", "created_at",
    )

    search_fields = (
        "title","description",
    )

class CartAdmin(admin.ModelAdmin):
    list_display = ("cart_id","student","course","added_at",)

    list_filter = ("added_at",)

    search_fields = ("student__first_name","student__last_name","student__email","course__title",)