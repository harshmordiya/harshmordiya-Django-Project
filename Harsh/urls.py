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

urlpatterns = [
    path('', views.home_view, name='home'),
    path('admin/', admin.site.urls),
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("logout/", logout_view, name="logout"),
    path("forgot-password/", forgot_password_view, name="forgot_password"),
    path("verify-otp/", verify_otp_view, name="verify_otp"),
    path("reset-password/", reset_password_view, name="reset_password"),
    # Course Catalog & Details
    path("courses/", views.course_list_view, name="course_list"),
    path("courses/<int:course_id>/", views.course_detail_view, name="course_detail"),

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

    # Course Content / Curriculum Management
    path("courses/<int:course_id>/content/", views.course_content_manage_view, name="course_content_manage"),
    path("courses/<int:course_id>/content/add/", views.course_content_add_view, name="course_content_add"),
    path("courses/content/<int:content_id>/edit/", views.course_content_edit_view, name="course_content_edit"),
    path("courses/content/<int:content_id>/delete/", views.course_content_delete_view, name="course_content_delete"),
]
