"""
URL configuration for Harsh project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from core import views

from core.views import (
    dashboard_view,
    login_view,
    logout_view,
    register_view,
    forgot_password_view,
    verify_otp_view,
    reset_password_view,
)

from django.views.generic import RedirectView

urlpatterns = [
    path('', views.home_view, name='home'),
    path('admin/', admin.site.urls),
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("accounts/login/", RedirectView.as_view(pattern_name="login", permanent=False, query_string=True)),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("profile/", views.user_profile_dispatcher_view, name="profile"),
    path("profile/edit/", views.student_profile_edit_view, name="profile_edit_legacy"),
    path("student/profile/", views.student_profile_view, name="student_profile"),
    path("student/profile/edit/", views.student_profile_edit_view, name="student_profile_edit"),
    path("student/profile/alt/", views.student_profile_view, name="student_profile_alt"),
    path("student/profile/edit/alt/", views.student_profile_edit_view, name="student_profile_edit_alt"),
    path("instructor/profile/", views.instructor_profile_view, name="instructor_profile"),
    path("instructor/profile/edit/", views.instructor_profile_edit_view, name="instructor_profile_edit"),
    path("students/<int:student_id>/profile/", views.student_profile_detail_view, name="student_profile_detail"),
    path("logout/", logout_view, name="logout"),
    path("forgot-password/", forgot_password_view, name="forgot_password"),
    path("verify-otp/", verify_otp_view, name="verify_otp"),
    path("reset-password/", reset_password_view, name="reset_password"),
    # Course Catalog & Details
    path("courses/", views.course_list_view, name="course_list"),
    path("courses/manage/", views.course_manage_all_view, name="course_manage_all"),
    path("courses/<int:course_id>/", views.course_detail_view, name="course_detail"),

    # Members & Community Directories (Students & Faculty)
    path("instructors/", views.instructor_list_view, name="instructor_list"),
    path("instructors/<int:instructor_id>/contact/", views.contact_instructor_view, name="contact_instructor"),
    path("students/", views.student_list_view, name="student_list"),
    path("directory/", views.directory_view, name="directory"),

    # Course Creation Routes (Instructor/Staff)
    path("courses/create/", views.course_create_view, name="course_create"),
    path("courses/add/", views.course_add_view, name="course_add"),
    path("instructor/courses/create/", views.instructor_course_create_view, name="instructor_course_create"),
    path("instructor/courses/add/", views.instructor_course_create_view, name="instructor_course_add"),

    # Course Update/Edit Routes
    path("courses/<int:course_id>/edit/", views.course_edit_view, name="course_edit"),
    path("courses/<int:course_id>/update/", views.course_update_view, name="course_update"),
    path("instructor/courses/<int:course_id>/edit/", views.instructor_course_edit_view, name="instructor_course_edit"),

    # Course Delete Routes
    path("courses/<int:course_id>/delete/", views.course_delete_view, name="course_delete"),
    path("instructor/courses/<int:course_id>/delete/", views.instructor_course_delete_view, name="instructor_course_delete"),

    # Shopping Cart & Checkout
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:course_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:cart_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("payment/callback/", views.payment_callback, name="payment_callback"),

    # Instructor Portal
    path("instructor/courses/", views.instructor_courses_view, name="instructor_courses"),
    path("instructor/dashboard/", views.instructor_courses_view, name="instructor_dashboard"),
    path("instructor/messages/", views.instructor_messages_view, name="instructor_messages"),
    path("instructor/messages/<int:message_id>/reply/", views.instructor_message_reply_view, name="instructor_message_reply"),

    # Course Content / Curriculum & Notes/Video Upload Management
    path("courses/<int:course_id>/content/", views.course_content_manage_view, name="course_content_manage"),
    path("courses/<int:course_id>/content/add/", views.course_content_add_view, name="course_content_add"),
    path("courses/<int:course_id>/upload-notes/", views.course_content_add_view, name="course_upload_notes"),
    path("courses/<int:course_id>/upload-material/", views.course_content_add_view, name="course_upload_material"),
    path("courses/content/<int:content_id>/edit/", views.course_content_edit_view, name="course_content_edit"),
    path("courses/content/<int:content_id>/delete/", views.course_content_delete_view, name="course_content_delete"),
    path("courses/content/<int:content_id>/reorder/<str:direction>/", views.course_content_reorder_view, name="course_content_reorder"),

    # Custom EduLearn Administrator Portal & Dashboards
    path("admin-dashboard/", views.admin_dashboard_view, name="admin_dashboard"),
    path("admin-dashboard/students/", views.admin_students_view, name="admin_students"),
    path("admin-dashboard/students/<int:student_id>/delete/", views.admin_student_delete_view, name="admin_student_delete"),
    path("admin-dashboard/instructors/", views.admin_instructors_view, name="admin_instructors"),
    path("admin-dashboard/instructors/<int:instructor_id>/delete/", views.admin_instructor_delete_view, name="admin_instructor_delete"),
    path("admin-dashboard/users/<int:user_id>/toggle-status/", views.admin_user_toggle_status_view, name="admin_user_toggle_status"),
    path("admin-dashboard/courses/", views.admin_courses_view, name="admin_courses"),
    path("admin-dashboard/courses/<int:course_id>/toggle-status/", views.admin_course_toggle_status_view, name="admin_course_toggle_status"),
    path("admin-dashboard/enrollments/", views.admin_enrollments_view, name="admin_enrollments"),
    path("admin-dashboard/enrollments/<int:enrollment_id>/status/<str:new_status>/", views.admin_enrollment_update_status_view, name="admin_enrollment_update_status"),
    path("admin-dashboard/payments/", views.admin_payments_view, name="admin_payments"),
]

# Serve user-uploaded media files in development
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

