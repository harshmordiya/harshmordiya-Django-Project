from django.contrib import admin

# Register your models here.
from .models import (
    Admin,
    Student,
    Instructor,
    UserProfile,
    PasswordResetOTP,
    Course,
)

admin.site.register(Admin)
admin.site.register(Student)
admin.site.register(Instructor)
admin.site.register(UserProfile)
admin.site.register(PasswordResetOTP)
admin.site.register(Course)