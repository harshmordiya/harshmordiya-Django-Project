from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

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

urlpatterns = [
    path('', views.home_view, name='home'),
    path('admin/', admin.site.urls),

    # Authentication & Accounts
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("accounts/login/", RedirectView.as_view(pattern_name="login", permanent=False, query_string=True)),
    path("forgot-password/", forgot_password_view, name="forgot_password"),
    path("verify-otp/", verify_otp_view, name="verify_otp"),
    path("reset-password/", reset_password_view, name="reset_password"),

    # Dashboard & Profiles
    path("dashboard/", dashboard_view, name="dashboard"),
    path("profile/", views.user_profile_dispatcher_view, name="profile"),
    path("profile/edit/", views.student_profile_edit_view, name="profile_edit_legacy"),
    path("student/profile/", views.student_profile_view, name="student_profile"),
    path("student/profile/edit/", views.student_profile_edit_view, name="student_profile_edit"),
    path("student/profile/alt/", views.student_profile_view, name="student_profile_alt"),
    path("student/profile/edit/alt/", views.student_profile_edit_view, name="student_profile_edit_alt"),
    path("students/<int:student_id>/profile/", views.student_profile_detail_view, name="student_profile_detail"),
    path("instructor/profile/", views.instructor_profile_view, name="instructor_profile"),
    path("instructor/profile/edit/", views.instructor_profile_edit_view, name="instructor_profile_edit"),

    # Course Catalog & Management 
    path("courses/", views.course_list_view, name="course_list"),
    path("courses/manage/", views.course_manage_all_view, name="course_manage_all"),
    path("courses/<int:course_id>/", views.course_detail_view, name="course_detail"),
    path("courses/create/", views.course_create_view, name="course_create"),
    path("courses/add/", views.course_add_view, name="course_add"),
    path("courses/<int:course_id>/edit/", views.course_edit_view, name="course_edit"),
    path("courses/<int:course_id>/update/", views.course_update_view, name="course_update"),
    path("courses/<int:course_id>/delete/", views.course_delete_view, name="course_delete"),

    # Course Content & Curriculum
    path("courses/<int:course_id>/content/", views.course_content_manage_view, name="course_content_manage"),
    path("courses/<int:course_id>/content/add/", views.course_content_add_view, name="course_content_add"),
    path("courses/<int:course_id>/upload-notes/", views.course_content_add_view, name="course_upload_notes"),
    path("courses/<int:course_id>/upload-material/", views.course_content_add_view, name="course_upload_material"),
    path("courses/content/<int:content_id>/edit/", views.course_content_edit_view, name="course_content_edit"),
    path("courses/content/<int:content_id>/delete/", views.course_content_delete_view, name="course_content_delete"),
    path("courses/content/<int:content_id>/reorder/<str:direction>/", views.course_content_reorder_view, name="course_content_reorder"),

    # Quizzes & Assessments
    path("quiz/<int:quiz_id>/attempt/", views.quiz_attempt_view, name="quiz_attempt"),
    path("quiz/attempt/<int:attempt_id>/result/", views.quiz_result_view, name="quiz_result"),
    path("content/<int:content_id>/quiz/", views.course_content_quiz_dispatch_view, name="content_quiz_dispatch"),

    # Instructor Quiz & Question Management
    path("instructor/courses/<int:course_id>/quizzes/", views.instructor_course_quizzes_view, name="instructor_course_quizzes"),
    path("instructor/courses/<int:course_id>/quizzes/create/", views.instructor_quiz_create_view, name="instructor_quiz_create"),
    path("instructor/quizzes/<int:quiz_id>/edit/", views.instructor_quiz_edit_view, name="instructor_quiz_edit"),
    path("instructor/quizzes/<int:quiz_id>/delete/", views.instructor_quiz_delete_view, name="instructor_quiz_delete"),
    path("instructor/quizzes/<int:quiz_id>/questions/", views.instructor_quiz_questions_view, name="instructor_quiz_questions"),
    path("instructor/quizzes/<int:quiz_id>/questions/add/", views.instructor_question_create_view, name="instructor_question_create"),
    path("instructor/questions/<int:question_id>/edit/", views.instructor_question_edit_view, name="instructor_question_edit"),
    path("instructor/questions/<int:question_id>/delete/", views.instructor_question_delete_view, name="instructor_question_delete"),
    path("instructor/content/<int:content_id>/manage-quiz/", views.instructor_content_quiz_manage_view, name="instructor_content_quiz_manage"),

    # Instructor Portal & Actions
    path("instructor/courses/", views.instructor_courses_view, name="instructor_courses"),
    path("instructor/dashboard/", views.instructor_courses_view, name="instructor_dashboard"),
    path("instructor/courses/create/", views.instructor_course_create_view, name="instructor_course_create"),
    path("instructor/courses/add/", views.instructor_course_create_view, name="instructor_course_add"),
    path("instructor/courses/<int:course_id>/edit/", views.instructor_course_edit_view, name="instructor_course_edit"),
    path("instructor/courses/<int:course_id>/delete/", views.instructor_course_delete_view, name="instructor_course_delete"),
    path("instructor/messages/", views.instructor_messages_view, name="instructor_messages"),
    path("instructor/messages/<int:message_id>/reply/", views.instructor_message_reply_view, name="instructor_message_reply"),

    # Directories & Contact
    path("instructors/", views.instructor_list_view, name="instructor_list"),
    path("instructors/<int:instructor_id>/contact/", views.contact_instructor_view, name="contact_instructor"),
    path("students/", views.student_list_view, name="student_list"),
    path("directory/", views.directory_view, name="directory"),

    # Shopping Cart & Razorpay Checkout
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:course_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:cart_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("payment/callback/", views.payment_callback, name="payment_callback"),

    # Administration Portal
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

    # Information & Support Pages
    path("help/", views.help_center_view, name="help_center"),
    path("help-center/", views.help_center_view, name="help_center_alt"),
    path("privacy-policy/", views.privacy_policy_view, name="privacy_policy"),
    path("terms-of-service/", views.terms_of_service_view, name="terms_of_service"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
