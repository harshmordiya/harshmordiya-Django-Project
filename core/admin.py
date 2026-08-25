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
class Cartadmin(admin.ModelAdmin):
    list_display = (
        "cart_id","student",
        "course","added_at",
    )

    list_filter = ("added_at",)

    search_fields = ("student_first_name","stduent_last_name","course_title",)