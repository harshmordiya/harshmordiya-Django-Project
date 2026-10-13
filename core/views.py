import random 
import razorpay

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
from functools import wraps
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse

# Create your views here.

from .forms import RegistrationForm, CourseForm, CourseContentForm
from .models import Cart, Course, CourseContent, PasswordResetOTP, Student, UserProfile, Payment, Enrollment, Instructor


def get_user_role(user):
    """
    Safely determine the effective role of a user: 'admin', 'instructor', or 'student'.
    - Superusers and staff members are always recognized as 'admin'.
    - Users with UserProfile role 'admin' are 'admin'.
    - Users with UserProfile role 'instructor' or an Instructor record are 'instructor'.
    - Default fallback is 'student'.
    """
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser or user.is_staff:
        return "admin"
    profile = UserProfile.objects.filter(user=user).first()
    if profile:
        return profile.role
    if Instructor.objects.filter(email=user.email).exists():
        return "instructor"
    return "student"


def is_admin_user(user):
    """
    Check if a user is an authorized administrator.
    True if user is superuser, staff, or has UserProfile role == 'admin'.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    profile = UserProfile.objects.filter(user=user).first()
    return bool(profile and profile.role == "admin")


def ensure_user_profile(user):
    """
    Safely retrieves or heals the UserProfile for an authenticated user.
    Ensures superusers/staff are automatically synchronized to 'admin' role
    so they are never erroneously displayed or treated as a student.
    """
    if not user or not user.is_authenticated:
        return None
    role = get_user_role(user)
    profile = UserProfile.objects.filter(user=user).first()
    if profile:
        if (user.is_superuser or user.is_staff) and profile.role != "admin":
            profile.role = "admin"
            profile.save(update_fields=["role"])
        return profile
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"role": role}
    )
    return profile


def admin_required(view_func):
    """
    Decorator to ensure the logged-in user is authenticated and is an administrator.
    Strictly denies access to ordinary students and instructors.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        if not is_admin_user(request.user):
            messages.error(request, "Access restricted: Administrator privileges are required to view that page.")
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


razorpay_client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    )
)

def home_view(request):
    courses = Course.objects.filter(is_active=True).select_related("instructor").order_by("-created_at")[:6]
    categories = Course.CATEGORY_CHOICES
    total_courses = Course.objects.filter(is_active=True).count()
    total_students = Student.objects.count()
    total_instructors = Instructor.objects.count()

    return render(
        request,
        "home.html",
        {
            "courses": courses,
            "categories": categories,
            "total_courses": total_courses,
            "total_students": total_students,
            "total_instructors": total_instructors,
        }
    )

def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            messages.success(request, f"Account created successfully for {user.username}! Please log in to get started.")
            return redirect("login")
        else:
            messages.error(request, "Registration failed. Please correct the highlighted errors below.")

    else:
        form = RegistrationForm()

    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username_input = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username_input,
            password=password
        )

        # Allow logging in with email address as well
        if user is None and "@" in username_input:
            user_by_email = User.objects.filter(email__iexact=username_input).first()
            if user_by_email:
                user = authenticate(
                    request,
                    username=user_by_email.username,
                    password=password
                )

        if user is not None:
            login(request, user)
            profile = ensure_user_profile(user)
            role = get_user_role(user)
            role_display = f" ({role.title()})" if role else ""
            messages.success(request, f"Welcome back, {user.first_name or user.username}! You are now signed in{role_display}.")

            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)
            if is_admin_user(user):
                return redirect("admin_dashboard")
            if role == "instructor":
                return redirect("instructor_courses")
            return redirect("dashboard")

        messages.error(request, "Invalid username or password. Please try again.")
        return render(
            request,
            "login.html",
            {"error": "Invalid username or password."}
        )

    return render(request, "login.html")


@login_required
def dashboard_view(request):
    profile = ensure_user_profile(request.user)
    user_role = get_user_role(request.user)
    is_admin = is_admin_user(request.user)

    # Safely query student profile associated with user without creating duplicates
    student = get_student_for_user(request.user)

    if student:
        enrollments = (
            Enrollment.objects.filter(
                student=student,
                status__in=["active", "completed"]
            )
            .select_related("course", "course__instructor")
            .order_by("-enrollment_date")
        )
    else:
        enrollments = Enrollment.objects.none()

    total_enrolled = enrollments.count()

    # For instructors, also fetch courses they have authored/created
    instructor = None
    authored_courses = Course.objects.none()
    if user_role == "instructor":
        instructor = get_instructor_for_user(request.user)
        if instructor:
            authored_courses = (
                Course.objects.filter(instructor=instructor)
                .annotate(
                    active_enrollments=Count(
                        "enrollments",
                        filter=Q(enrollments__status__in=["active", "completed"])
                    )
                )
                .order_by("-created_at")
            )

    return render(
        request,
        "dashboard.html",
        {
            "profile": profile,
            "user_role": user_role,
            "is_admin": is_admin,
            "student": student,
            "enrollments": enrollments,
            "total_enrolled": total_enrolled,
            "instructor": instructor,
            "authored_courses": authored_courses,
            "total_authored": authored_courses.count(),
        }
    )




def logout_view(request):
    if request.user.is_authenticated:
        username = request.user.first_name or request.user.username
        logout(request)
        messages.info(request, f"Goodbye {username}! You have been logged out successfully.")
    else:
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect("login")


def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account was found with this email address.")
            return render(
                request,
                "forgot_password.html",
                {"error": "No account found with this email."}
            )

        otp = str(random.randint(100000, 999999))

        PasswordResetOTP.objects.filter(
            user=user,
            is_verified=False
        ).delete()

        PasswordResetOTP.objects.create(
            user=user,
            otp=otp
        )

        try:
            send_mail(
                subject="EduLearn Password Reset Verification Code",
                message=(
                    f"Hello {user.first_name or user.username},\n\n"
                    f"Your 6-digit verification code is: {otp}\n\n"
                    f"This code will expire in 5 minutes.\n\n"
                    "If you did not request this password reset, please ignore this email.\n\n"
                    "— EduLearn Security Team"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@edulearn.local"),
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as mail_err:
            print(f"[EMAIL ERROR] Failed to send email via {settings.EMAIL_BACKEND}: {mail_err}")
            if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
                messages.error(request, f"Email delivery failed: {mail_err}. Please check your SMTP settings.")
                return render(request, "forgot_password.html")

        request.session["reset_email"] = email
        messages.success(request, f"A 6-digit verification code has been sent to {email}.")
        return redirect("verify_otp")

    return render(request, "forgot_password.html")


def verify_otp_view(request):
    email = request.session.get("reset_email")

    if not email:
        messages.warning(request, "Please request a password reset code first.")
        return redirect("forgot_password")

    # Helper for local development testing when Console email backend is active
    dev_otp = None
    if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
        user = User.objects.filter(email=email).first()
        if user:
            otp_record = PasswordResetOTP.objects.filter(user=user, is_verified=False).order_by("-created_at").first()
            if otp_record:
                dev_otp = otp_record.otp

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()

        try:
            user = User.objects.get(email=email)
            otp_record = PasswordResetOTP.objects.filter(
                user=user,
                otp=entered_otp,
                is_verified=False
            ).latest("created_at")

        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
            messages.error(request, "Invalid OTP code entered. Please try again.")
            return render(
                request,
                "verify_otp.html",
                {"error": "Invalid OTP.", "dev_otp": dev_otp}
            )

        # OTP expires after 5 minutes
        elapsed_time = timezone.now() - otp_record.created_at

        if elapsed_time.total_seconds() > 300:
            otp_record.delete()
            messages.error(request, "OTP code has expired. Please request a new code.")
            return render(
                request,
                "verify_otp.html",
                {"error": "OTP has expired. Please request a new OTP.", "dev_otp": None}
            )

        otp_record.is_verified = True
        otp_record.save()

        request.session["otp_verified"] = True
        messages.success(request, "OTP code verified successfully! Please choose a new password.")
        return redirect("reset_password")

    return render(request, "verify_otp.html", {"dev_otp": dev_otp})


def reset_password_view(request):
    email = request.session.get("reset_email")
    otp_verified = request.session.get("otp_verified")

    if not email or not otp_verified:
        messages.warning(request, "Session expired or invalid. Please request a password reset.")
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match. Please re-enter both fields.")
            return render(
                request,
                "reset_password.html",
                {"error": "Passwords do not match."}
            )

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(
                request,
                "reset_password.html",
                {"error": "Password must be at least 8 characters."}
            )

        user = User.objects.get(email=email)

        user.set_password(password)
        user.save()

        request.session.pop("reset_email", None)
        request.session.pop("otp_verified", None)

        messages.success(request, "Your password has been reset successfully! You can now log in.")
        return redirect("login")

    return render(request, "reset_password.html")

from django.db.models import Q


def course_list_view(request):

    courses = Course.objects.filter(
        is_active=True
    )

    search_query = request.GET.get("q", "").strip()

    category_filter = request.GET.get(
        "category",
        ""
    ).strip()


    # Search by title or category

    if search_query:

        normalized_query = search_query.lower().replace(
            " ",
            "_"
        )

        courses = courses.filter(

            Q(title__icontains=search_query) |

            Q(category__icontains=search_query) |

            Q(category__icontains=normalized_query)

        )


    # Category filter

    if category_filter:

        courses = courses.filter(
            category=category_filter
        )


    # Latest courses first

    courses = courses.order_by(
        "-created_at"
    )


    # Pagination - 6 courses per page

    paginator = Paginator(
        courses,
        6
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )


    return render(
        request,
        "course_list.html",
        {
            "courses": page_obj,
            "page_obj": page_obj,
            "search_query": search_query,
            "category_filter": category_filter,
            "categories": Course.CATEGORY_CHOICES,
        }
    )

def course_detail_view(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)

    # Check if the authenticated user is authorized to manage this course
    is_course_manager = False
    is_enrolled = False
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            is_course_manager = True
        else:
            profile = UserProfile.objects.filter(user=request.user).first()
            if profile and profile.role == "admin":
                is_course_manager = True
            elif profile and profile.role == "instructor":
                instructor = get_instructor_for_user(request.user)
                if instructor and (course.instructor == instructor or course.instructor is None):
                    is_course_manager = True

        student = get_student_for_user(request.user)
        if student:
            is_enrolled = Enrollment.objects.filter(student=student, course=course, status__in=["active", "completed"]).exists()

    # If the course is inactive, only allow course managers to view it
    if not course.is_active and not is_course_manager:
        raise Http404("Course not found or currently unavailable.")

    contents = course.contents.all().order_by("order", "content_id")

    return render(
        request,
        "course_detail.html",
        {
            "course": course,
            "contents": contents,
            "is_enrolled": is_enrolled,
            "is_course_manager": is_course_manager,
        }
    )


def instructor_list_view(request):
    """
    Public / platform view listing all registered instructors and faculty members.
    Displays faculty profiles, specializations, authored courses, and student reach.
    """
    q = request.GET.get("q", "").strip()
    specialization_filter = request.GET.get("specialization", "").strip()

    instructors_qs = Instructor.objects.annotate(
        courses_count=Count("course", distinct=True),
        students_count=Count(
            "course__enrollments",
            filter=Q(course__enrollments__status__in=["active", "completed"]),
            distinct=True
        )
    ).order_by("-hire_date")

    if q:
        instructors_qs = instructors_qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(specialization__icontains=q)
        )

    if specialization_filter:
        instructors_qs = instructors_qs.filter(specialization__iexact=specialization_filter)

    # Distinct specializations for filter pills
    specializations = (
        Instructor.objects.exclude(specialization="")
        .values_list("specialization", flat=True)
        .distinct()
        .order_by("specialization")
    )

    paginator = Paginator(instructors_qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "instructors": page_obj,
        "page_obj": page_obj,
        "total_instructors": instructors_qs.count(),
        "search_query": q,
        "specialization_filter": specialization_filter,
        "specializations": specializations,
        "active_tab": "instructors",
    }
    return render(request, "instructor_list.html", context)


def student_list_view(request):
    """
    Platform view listing all registered students in the EduLearn community.
    Displays student profiles, joined dates, and active learning enrollments.
    """
    q = request.GET.get("q", "").strip()

    students_qs = Student.objects.annotate(
        enrollments_count=Count(
            "enrollments",
            filter=Q(enrollments__status__in=["active", "completed"]),
            distinct=True
        )
    ).order_by("-enrollment_date")

    if q:
        students_qs = students_qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q) |
            Q(address__icontains=q)
        )

    paginator = Paginator(students_qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "students": page_obj,
        "page_obj": page_obj,
        "total_students": students_qs.count(),
        "search_query": q,
        "active_tab": "students",
    }
    return render(request, "student_list.html", context)


def directory_view(request):
    """
    Unified directory view listing all registered students and instructors.
    Provides tabbed navigation, live platform counts, and search across members.
    """
    q = request.GET.get("q", "").strip()
    active_tab = request.GET.get("tab", "all").strip().lower()
    if active_tab not in ["all", "instructors", "students"]:
        active_tab = "all"

    instructors_qs = Instructor.objects.annotate(
        courses_count=Count("course", distinct=True),
        students_count=Count(
            "course__enrollments",
            filter=Q(course__enrollments__status__in=["active", "completed"]),
            distinct=True
        )
    ).order_by("-hire_date")

    students_qs = Student.objects.annotate(
        enrollments_count=Count(
            "enrollments",
            filter=Q(enrollments__status__in=["active", "completed"]),
            distinct=True
        )
    ).order_by("-enrollment_date")

    if q:
        instructors_qs = instructors_qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(specialization__icontains=q)
        )
        students_qs = students_qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q)
        )

    context = {
        "instructors": instructors_qs,
        "students": students_qs,
        "total_instructors": Instructor.objects.count(),
        "total_students": Student.objects.count(),
        "total_courses": Course.objects.filter(is_active=True).count(),
        "search_query": q,
        "active_tab": active_tab,
    }
    return render(request, "directory.html", context)

@login_required
def add_to_cart(request, course_id):
    student = get_student_for_user(request.user)

    if not student:
        messages.error(
            request,
            "No student profile found for this account. Only registered students can enroll in courses."
        )
        return redirect("course_list")

    course = get_object_or_404(
        Course,
        course_id=course_id
    )

    # Check if student is already enrolled in this course
    is_already_enrolled = Enrollment.objects.filter(
        student=student,
        course=course,
        status="active"
    ).exists()

    if is_already_enrolled:
        messages.info(
            request,
            f"You are already actively enrolled in '{course.title}'."
        )
        return redirect("course_detail", course_id=course.course_id)

    cart_item, created = Cart.objects.get_or_create(
        student=student,
        course=course
    )

    if created:
        messages.success(
            request,
            f"'{course.title}' was added to your cart."
        )
    else:
        messages.info(
            request,
            f"'{course.title}' is already in your cart."
        )

    return redirect("cart")

@login_required
def remove_from_cart(request, cart_id):
    try:
        student = Student.objects.get(
            email=request.user.email
        )
    except Student.DoesNotExist:
        messages.error(
            request,
            "Student profile not found."
        )
        return redirect("cart")

    cart_item = Cart.objects.filter(
        cart_id=cart_id,
        student=student
    ).first()

    if not cart_item:
        messages.warning(
            request,
            "Item was not found in your cart."
        )
        return redirect("cart")

    course_title = cart_item.course.title
    cart_item.delete()

    messages.success(
        request,
        f"'{course_title}' was removed from your cart."
    )

    return redirect("cart")

# @login_required
# def cart_view(request):

#     print("========== CART VIEW ==========")
#     print("LOGGED USER:", request.user.username)
#     print("USER EMAIL:", repr(request.user.email))
#     print("AUTHENTICATED:", request.user.is_authenticated)

#     student = Student.objects.filter(
#         email=request.user.email
#     ).first()

#     print("FOUND STUDENT:", student)

#     if not student:
#         print("NO STUDENT - REDIRECTING TO COURSES")

#         messages.error(
#             request,
#             "No student profile found for this account."
#         )

#         return redirect("course_list")

#     cart_items = Cart.objects.filter(
#         student=student
#     ).select_related("course")

#     print("CART ITEMS:", list(cart_items))

#     return render(
#         request,
#         "cart.html",
#         {
#             "cart_items": cart_items
#         }
#     )

@login_required
def cart_view(request):

    student = get_student_for_user(request.user)

    if not student:
        messages.error(
            request,
            "No student profile found for this account."
        )
        return redirect("course_list")

    cart_items = Cart.objects.filter(
        student=student
    ).select_related("course")

    return render(
        request,
        "cart.html",
        {
            "cart_items": cart_items,
        }
    )

@login_required
def checkout_view(request):

    student = get_student_for_user(request.user)

    if not student:
        messages.error(
            request,
            "No student profile found for this account."
        )
        return redirect("course_list")

    cart_items = Cart.objects.filter(
        student=student
    ).select_related("course")

    if not cart_items.exists():
        messages.warning(
            request,
            "Your cart is empty."
        )
        return redirect("cart")

    total_amount = sum(
        item.course.price for item in cart_items
    )

    amount_paise = int(total_amount * 100)

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    # Create Razorpay order
    order = client.order.create(
        data={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"cart_{student.student_id}",
        }
    )

    # Save Razorpay order in our database BEFORE payment
    Payment.objects.create(
        student=student,
        razorpay_order_id=order["id"],
        amount=total_amount,
        status="created",
    )

    context = {
        "student": student,
        "cart_items": cart_items,
        "total_amount": total_amount,
        "amount_paise": amount_paise,
        "amount_in_paise": amount_paise,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": order["id"],
    }

    return render(
        request,
        "checkout.html",
        context
    )

@csrf_exempt
def payment_callback(request):

    if request.method != "POST":
        return redirect("cart")

    payment_id = request.POST.get("razorpay_payment_id")
    order_id = request.POST.get("razorpay_order_id")
    signature = request.POST.get("razorpay_signature")

    if not payment_id or not order_id or not signature:
        messages.error(
            request,
            "Payment information is incomplete."
        )
        return redirect("cart")

    try:
        payment = Payment.objects.get(
            razorpay_order_id=order_id
        )
    except Payment.DoesNotExist:
        messages.error(
            request,
            "Payment order was not found."
        )
        return redirect("cart")

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
    )

    try:

        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })

        # Payment verified successfully
        payment.razorpay_payment_id = payment_id
        payment.razorpay_signature = signature
        payment.status = "verified"
        payment.save()

        cart_items = Cart.objects.filter(
    student=payment.student
)

        for cart_item in cart_items:
            Enrollment.objects.get_or_create(
                student=payment.student,
                course=cart_item.course,
                defaults={
                    "status": "active"
                }
            )

        cart_items.delete()

        # Remove purchased courses from cart
        student = Student.objects.filter(
            student_id=payment.student_id
        ).first()

        if student:
            student.enrollment_date = timezone.now()
            student.save(update_fields=["enrollment_date"])

        if student:
            Cart.objects.filter(
                student=student
            ).delete()

        messages.success(
            request,
            "Payment successful! Your payment has been verified."
        )

        return redirect("course_list")

    except razorpay.errors.SignatureVerificationError:

        payment.status = "failed"
        payment.save()

        messages.error(
            request,
            "Payment verification failed."
        )

        return redirect("cart")
    
    
# ==============================================================================
# Instructor Portal Helpers, Decorators, and Views
# ==============================================================================

def get_student_for_user(user):
    """
    Safely retrieves the Student profile for an authenticated user.
    If the user has role 'student' in UserProfile but lacks a Student record,
    it safely auto-heals and creates one using the user's details without creating duplicates.
    """
    if not user or not user.is_authenticated:
        return None

    student = Student.objects.filter(email__iexact=user.email).first()
    if not student:
        role = get_user_role(user)
        if role == "student":
            student, _ = Student.objects.get_or_create(
                email=user.email,
                defaults={
                    "first_name": user.first_name or user.username,
                    "last_name": user.last_name or "",
                    "phone": "",
                    "address": "",
                    "enrollment_date": timezone.now(),
                }
            )
    return student


def get_instructor_for_user(user):
    """
    Safely retrieves the Instructor profile for an authenticated user.
    If the user has role 'instructor' in UserProfile but lacks an Instructor record,
    it safely auto-heals and creates one using the user's details without creating duplicates.
    """
    if not user.is_authenticated:
        return None

    # Check case-insensitively by email
    instructor = Instructor.objects.filter(email__iexact=user.email).first()
    if not instructor:
        profile = UserProfile.objects.filter(user=user).first()
        if profile and profile.role == "instructor":
            # Auto-heal profile
            instructor, _ = Instructor.objects.get_or_create(
                email=user.email,
                defaults={
                    "first_name": user.first_name or user.username,
                    "last_name": user.last_name or "",
                    "phone": "",
                    "specialization": "General",
                }
            )
    return instructor


def instructor_required(view_func):
    """
    Decorator to ensure the logged-in user is authenticated, has the instructor role,
    and has a valid Instructor profile.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Please log in to access the Instructor Portal.")
            return redirect("login")

        profile = UserProfile.objects.filter(user=request.user).first()
        if not profile or profile.role != "instructor":
            messages.error(request, "Access restricted. You must have an instructor account to view this page.")
            return redirect("dashboard")

        instructor = get_instructor_for_user(request.user)
        if not instructor:
            messages.error(request, "Could not initialize your instructor profile. Please contact support.")
            return redirect("dashboard")

        return view_func(request, *args, **kwargs)
    return _wrapped_view


@instructor_required
def instructor_courses_view(request):
    """
    Instructor Dashboard & Course Hub.
    Displays instructor metrics (total courses, active courses, student enrollments)
    and lists all courses authored by this instructor with management controls.
    """
    instructor = get_instructor_for_user(request.user)

    # Fetch instructor's courses with active and total enrollment counts
    courses = Course.objects.filter(
        instructor=instructor
    ).annotate(
        active_enrollments=Count(
            "enrollments",
            filter=Q(enrollments__status__in=["active", "completed"])
        ),
        total_enrollments_count=Count(
            "enrollments",
            filter=Q(enrollments__status__in=["active", "completed"])
        )
    ).order_by("-created_at")

    total_courses = courses.count()
    active_courses = courses.filter(is_active=True).count()
    inactive_courses = total_courses - active_courses

    # Real enrollment metrics across all courses by this instructor
    total_enrollments = Enrollment.objects.filter(
        course__instructor=instructor,
        status__in=["active", "completed"]
    ).count()

    unique_students = Enrollment.objects.filter(
        course__instructor=instructor,
        status__in=["active", "completed"]
    ).values("student").distinct().count()

    context = {
        "instructor": instructor,
        "courses": courses,
        "total_courses": total_courses,
        "active_courses": active_courses,
        "inactive_courses": inactive_courses,
        "total_enrollments": total_enrollments,
        "unique_students": unique_students,
    }

    return render(request, "instructor_courses.html", context)


@instructor_required
def instructor_course_create_view(request):
    """
    Allows instructors to create and publish a new course.
    The course is automatically associated with the authenticated instructor.
    """
    instructor = get_instructor_for_user(request.user)

    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = instructor
            course.save()
            messages.success(request, f'Course "{course.title}" was created successfully!')
            return redirect("instructor_courses")
        else:
            messages.error(request, "Failed to create course. Please review the highlighted errors below.")
    else:
        form = CourseForm()

    return render(
        request,
        "instructor_course_form.html",
        {
            "form": form,
            "title": "Create New Course",
            "subtitle": "Add a new course to your curriculum and make it available for students.",
            "is_edit": False,
            "instructor": instructor,
        }
    )


def can_manage_course(user, course):
    """
    Determines if a user has permission to manage (edit or delete) a course.
    - Superusers, staff, and admin role users can manage any course.
    - Instructors can only manage courses that they authored.
    """
    if not user.is_authenticated:
        return False, None
    if user.is_staff or user.is_superuser:
        return True, None
    profile = UserProfile.objects.filter(user=user).first()
    if profile and profile.role == "admin":
        return True, None
    if profile and profile.role == "instructor":
        instructor = get_instructor_for_user(user)
        if instructor and course.instructor == instructor:
            return True, instructor
    return False, None


@login_required
def instructor_course_edit_view(request, course_id):
    """
    Allows an instructor or admin to edit details of an existing course.
    Strictly verifies ownership or administrative privileges.
    """
    course = get_object_or_404(Course, course_id=course_id)

    allowed, instructor = can_manage_course(request.user, course)
    if not allowed:
        messages.error(request, "Unauthorized: You can only edit courses that belong to you.")
        return redirect("instructor_courses")

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            updated_course = form.save(commit=False)
            if not updated_course.instructor and instructor:
                updated_course.instructor = instructor
            updated_course.save()
            messages.success(request, f'Course "{course.title}" was updated successfully!')
            
            profile = UserProfile.objects.filter(user=request.user).first()
            if profile and profile.role == "instructor":
                return redirect("instructor_courses")
            return redirect("course_detail", course_id=course.course_id)
        else:
            messages.error(request, "Failed to update course. Please review the highlighted errors below.")
    else:
        form = CourseForm(instance=course)

    return render(
        request,
        "instructor_course_form.html",
        {
            "form": form,
            "course": course,
            "title": f"Edit Course: {course.title}",
            "subtitle": "Update details, syllabus description, duration, pricing, and availability.",
            "is_edit": True,
            "instructor": course.instructor or instructor,
        }
    )


@login_required
def instructor_course_delete_view(request, course_id):
    """
    Allows an instructor or admin to delete a course with confirmation.
    Strictly verifies ownership or administrative privileges. Requires a POST request to perform deletion.
    """
    course = get_object_or_404(Course, course_id=course_id)

    allowed, instructor = can_manage_course(request.user, course)
    if not allowed:
        messages.error(request, "Unauthorized: You can only delete courses that belong to you.")
        return redirect("instructor_courses")

    enrolled_count = course.enrollments.filter(status__in=["active", "completed"]).count()

    if request.method == "POST":
        title = course.title
        course.delete()
        messages.success(request, f'Course "{title}" was deleted permanently.')
        
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile and profile.role == "instructor":
            return redirect("instructor_courses")
        return redirect("course_list")

    return render(
        request,
        "instructor_course_confirm_delete.html",
        {
            "course": course,
            "instructor": course.instructor or instructor,
            "enrolled_count": enrolled_count,
        }
    )


# Course CRUD view aliases for flexible imports and routing
course_create_view = instructor_course_create_view
course_add_view = instructor_course_create_view
course_update_view = instructor_course_edit_view
course_edit_view = instructor_course_edit_view
course_delete_view = instructor_course_delete_view


# ---------------------------------------------------------
# Course Content Management Views
# ---------------------------------------------------------

@login_required
def course_content_manage_view(request, course_id):
    """
    Manage curriculum and lessons for a specific course.
    Instructors can only manage contents for their own courses.
    """
    course = get_object_or_404(Course, course_id=course_id)
    allowed, instructor = can_manage_course(request.user, course)
    if not allowed:
        messages.error(request, "Unauthorized: You can only manage content for your own courses.")
        return redirect("instructor_courses")

    contents = course.contents.all().order_by("order", "content_id")
    total_lessons = contents.count()
    video_count = contents.filter(content_type="video").count()
    document_count = contents.filter(content_type="document").count()
    preview_count = contents.filter(is_free_preview=True).count()
    notes_count = contents.filter(notes_file__isnull=False).exclude(notes_file="").count()

    return render(
        request,
        "course_content_manage.html",
        {
            "course": course,
            "contents": contents,
            "instructor": course.instructor or instructor,
            "total_lessons": total_lessons,
            "video_count": video_count,
            "document_count": document_count,
            "preview_count": preview_count,
            "notes_count": notes_count,
        }
    )


@login_required
def course_content_add_view(request, course_id):
    """
    Add a new lesson, video, document, or exercise to a course.
    """
    course = get_object_or_404(Course, course_id=course_id)
    allowed, instructor = can_manage_course(request.user, course)
    if not allowed:
        messages.error(request, "Unauthorized: You can only add content to your own courses.")
        return redirect("instructor_courses")

    if request.method == "POST":
        form = CourseContentForm(request.POST, request.FILES)
        if form.is_valid():
            content = form.save(commit=False)
            content.course = course
            content.save()
            messages.success(request, f'Lesson "{content.title}" was added successfully with your uploaded materials!')
            return redirect("course_content_manage", course_id=course.course_id)
        else:
            messages.error(request, "Failed to add lesson. Please review the highlighted errors below.")
    else:
        next_order = course.contents.count() + 1
        form = CourseContentForm(initial={"order": next_order})

    return render(
        request,
        "course_content_form.html",
        {
            "form": form,
            "course": course,
            "title": f"Upload Notes & Videos: {course.title}",
            "subtitle": "Add downloadable notes files (PDF, DOCX), lecture video URLs, and study materials.",
            "is_edit": False,
        }
    )


@login_required
def course_content_edit_view(request, content_id):
    """
    Edit details of an existing lesson or content module.
    """
    content = get_object_or_404(CourseContent, content_id=content_id)
    course = content.course
    allowed, instructor = can_manage_course(request.user, course)
    if not allowed:
        messages.error(request, "Unauthorized: You can only edit content for your own courses.")
        return redirect("instructor_courses")

    if request.method == "POST":
        form = CourseContentForm(request.POST, request.FILES, instance=content)
        if form.is_valid():
            form.save()
            messages.success(request, f'Lesson "{content.title}" updated successfully with your changes!')
            return redirect("course_content_manage", course_id=course.course_id)
        else:
            messages.error(request, "Failed to update lesson. Please review the highlighted errors below.")
    else:
        form = CourseContentForm(instance=content)

    return render(
        request,
        "course_content_form.html",
        {
            "form": form,
            "course": course,
            "content": content,
            "title": f"Edit Lesson: {content.title}",
            "subtitle": f"Update syllabus content for {course.title}.",
            "is_edit": True,
        }
    )


@login_required
def course_content_delete_view(request, content_id):
    """
    Delete a specific lesson or content module with safe confirmation.
    """
    content = get_object_or_404(CourseContent, content_id=content_id)
    course = content.course
    allowed, instructor = can_manage_course(request.user, course)
    if not allowed:
        messages.error(request, "Unauthorized: You can only delete content for your own courses.")
        return redirect("instructor_courses")

    if request.method == "POST":
        title = content.title
        course_id = course.course_id
        content.delete()
        messages.success(request, f'Lesson "{title}" was deleted.')
        return redirect("course_content_manage", course_id=course_id)

    return render(
        request,
        "course_content_confirm_delete.html",
        {
            "course": course,
            "content": content,
        }
    )


@login_required
def course_content_reorder_view(request, content_id, direction):
    """
    Reorder lesson sequence up or down within a course syllabus.
    """
    content = get_object_or_404(CourseContent, content_id=content_id)
    course = content.course
    allowed, instructor = can_manage_course(request.user, course)
    if not allowed:
        messages.error(request, "Unauthorized: You can only reorder lessons for your own courses.")
        return redirect("instructor_courses")

    items = list(course.contents.all().order_by("order", "content_id"))
    for idx, item in enumerate(items, start=1):
        if item.order != idx:
            item.order = idx
            item.save(update_fields=["order"])

    try:
        current_index = [item.content_id for item in items].index(content.content_id)
    except ValueError:
        return redirect("course_content_manage", course_id=course.course_id)

    if direction == "up" and current_index > 0:
        prev_item = items[current_index - 1]
        prev_item.order, content.order = content.order, prev_item.order
        prev_item.save(update_fields=["order"])
        content.save(update_fields=["order"])
        messages.success(request, f'Lesson "{content.title}" moved up.')
    elif direction == "down" and current_index < len(items) - 1:
        next_item = items[current_index + 1]
        next_item.order, content.order = content.order, next_item.order
        next_item.save(update_fields=["order"])
        content.save(update_fields=["order"])
        messages.success(request, f'Lesson "{content.title}" moved down.')

    return redirect("course_content_manage", course_id=course.course_id)


# Upload notes & video URL view aliases
course_upload_notes_view = course_content_add_view
course_upload_material_view = course_content_add_view


# ---------------------------------------------------------
# Custom EduLearn Administrator Portal Views
# ---------------------------------------------------------

@admin_required
def admin_dashboard_view(request):
    """
    Main EduLearn Custom Admin Dashboard overview with live KPI metrics,
    recent enrollments, recent payments, and system health statistics.
    """
    total_students = Student.objects.count()
    total_instructors = Instructor.objects.count()
    total_courses = Course.objects.count()
    active_courses = Course.objects.filter(is_active=True).count()
    inactive_courses = Course.objects.filter(is_active=False).count()

    total_enrollments = Enrollment.objects.count()
    active_enrollments = Enrollment.objects.filter(status="active").count()
    completed_enrollments = Enrollment.objects.filter(status="completed").count()
    cancelled_enrollments = Enrollment.objects.filter(status="cancelled").count()

    total_payments = Payment.objects.count()
    paid_payments = Payment.objects.filter(status__iexact="paid")
    total_revenue = paid_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_users = User.objects.count()

    recent_enrollments = (
        Enrollment.objects.select_related("student", "course", "course__instructor")
        .order_by("-enrollment_date")[:8]
    )
    recent_payments = (
        Payment.objects.select_related("student")
        .order_by("-created_at")[:8]
    )
    recent_courses = (
        Course.objects.select_related("instructor")
        .annotate(enrolled_count=Count("enrollments"))
        .order_by("-created_at")[:6]
    )
    recent_students = (
        Student.objects.annotate(enrolled_count=Count("enrollments"))
        .order_by("-student_id")[:6]
    )

    context = {
        "total_students": total_students,
        "total_instructors": total_instructors,
        "total_courses": total_courses,
        "active_courses": active_courses,
        "inactive_courses": inactive_courses,
        "total_enrollments": total_enrollments,
        "active_enrollments": active_enrollments,
        "completed_enrollments": completed_enrollments,
        "cancelled_enrollments": cancelled_enrollments,
        "total_payments": total_payments,
        "paid_payments_count": paid_payments.count(),
        "total_revenue": total_revenue,
        "total_users": total_users,
        "recent_enrollments": recent_enrollments,
        "recent_payments": recent_payments,
        "recent_courses": recent_courses,
        "recent_students": recent_students,
        "active_tab": "dashboard",
    }
    return render(request, "admin_dashboard.html", context)


@admin_required
def admin_students_view(request):
    """
    Administrator student management page.
    Lists all registered students with live course enrollments and payment statistics.
    """
    q = request.GET.get("q", "").strip()
    students_qs = Student.objects.annotate(
        enrollments_count=Count("enrollments", distinct=True),
        paid_total=Sum("payments__amount", filter=Q(payments__status__iexact="paid"))
    ).order_by("-student_id")

    if q:
        students_qs = students_qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q)
        )

    context = {
        "students": students_qs,
        "total_count": students_qs.count(),
        "search_query": q,
        "active_tab": "students",
    }
    return render(request, "admin_students.html", context)


@admin_required
def admin_instructors_view(request):
    """
    Administrator instructor management page.
    Lists all registered instructors with courses taught and student reach.
    """
    q = request.GET.get("q", "").strip()
    instructors_qs = Instructor.objects.annotate(
        courses_count=Count("course", distinct=True),
        students_count=Count("course__enrollments", filter=Q(course__enrollments__status__in=["active", "completed"]), distinct=True)
    ).order_by("-instructor_id")

    if q:
        instructors_qs = instructors_qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(specialization__icontains=q)
        )

    context = {
        "instructors": instructors_qs,
        "total_count": instructors_qs.count(),
        "search_query": q,
        "active_tab": "instructors",
    }
    return render(request, "admin_instructors.html", context)


@admin_required
def admin_courses_view(request):
    """
    Administrator course catalog management page.
    Displays all courses, pricing, instructor details, enrollment counts, and status controls.
    """
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "all")

    courses_qs = Course.objects.select_related("instructor").annotate(
        active_enrollments=Count("enrollments", filter=Q(enrollments__status__in=["active", "completed"]), distinct=True),
        lessons_count=Count("contents", distinct=True)
    ).order_by("-created_at")

    if status_filter == "active":
        courses_qs = courses_qs.filter(is_active=True)
    elif status_filter == "inactive":
        courses_qs = courses_qs.filter(is_active=False)

    if q:
        courses_qs = courses_qs.filter(
            Q(title__icontains=q) |
            Q(category__icontains=q) |
            Q(instructor__first_name__icontains=q) |
            Q(instructor__last_name__icontains=q)
        )

    context = {
        "courses": courses_qs,
        "total_count": courses_qs.count(),
        "active_courses_count": Course.objects.filter(is_active=True).count(),
        "inactive_courses_count": Course.objects.filter(is_active=False).count(),
        "status_filter": status_filter,
        "search_query": q,
        "active_tab": "courses",
    }
    return render(request, "admin_courses.html", context)


@admin_required
def admin_course_toggle_status_view(request, course_id):
    """
    Toggles course visibility status between Active and Draft/Inactive.
    """
    course = get_object_or_404(Course, course_id=course_id)
    course.is_active = not course.is_active
    course.save(update_fields=["is_active"])
    status_label = "Active (Published)" if course.is_active else "Draft (Hidden)"
    messages.success(request, f'Course "{course.title}" status changed to {status_label}.')
    return redirect("admin_courses")


@admin_required
def admin_enrollments_view(request):
    """
    Administrator enrollment tracking page.
    Shows all student enrollments, course affiliations, dates, and status management.
    """
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "all")

    enrollments_qs = Enrollment.objects.select_related(
        "student", "course", "course__instructor"
    ).order_by("-enrollment_date")

    if status_filter in ["active", "completed", "cancelled"]:
        enrollments_qs = enrollments_qs.filter(status=status_filter)

    if q:
        enrollments_qs = enrollments_qs.filter(
            Q(student__first_name__icontains=q) |
            Q(student__last_name__icontains=q) |
            Q(student__email__icontains=q) |
            Q(course__title__icontains=q)
        )

    context = {
        "enrollments": enrollments_qs,
        "total_count": enrollments_qs.count(),
        "active_count": Enrollment.objects.filter(status="active").count(),
        "completed_count": Enrollment.objects.filter(status="completed").count(),
        "cancelled_count": Enrollment.objects.filter(status="cancelled").count(),
        "status_filter": status_filter,
        "search_query": q,
        "active_tab": "enrollments",
    }
    return render(request, "admin_enrollments.html", context)


@admin_required
def admin_enrollment_update_status_view(request, enrollment_id, new_status):
    """
    Updates the status of an enrollment record (active, completed, cancelled).
    """
    enrollment = get_object_or_404(Enrollment, enrollment_id=enrollment_id)
    if new_status in ["active", "completed", "cancelled"]:
        enrollment.status = new_status
        enrollment.save(update_fields=["status"])
        messages.success(request, f'Enrollment #{enrollment.enrollment_id} updated to {new_status.title()}.')
    else:
        messages.error(request, f'Invalid status choice: {new_status}')
    return redirect("admin_enrollments")


@admin_required
def admin_payments_view(request):
    """
    Administrator payment and revenue reconciliation page.
    Tracks all transaction orders, payment IDs, amounts, and statuses.
    """
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "all")

    payments_qs = Payment.objects.select_related("student").order_by("-created_at")

    if status_filter != "all":
        payments_qs = payments_qs.filter(status__iexact=status_filter)

    if q:
        payments_qs = payments_qs.filter(
            Q(razorpay_order_id__icontains=q) |
            Q(razorpay_payment_id__icontains=q) |
            Q(student__email__icontains=q) |
            Q(student__first_name__icontains=q) |
            Q(student__last_name__icontains=q)
        )

    total_volume = Payment.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    paid_volume = Payment.objects.filter(status__iexact="paid").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_tx = Payment.objects.count()
    paid_tx = Payment.objects.filter(status__iexact="paid").count()

    context = {
        "payments": payments_qs,
        "total_count": payments_qs.count(),
        "total_volume": total_volume,
        "paid_volume": paid_volume,
        "total_tx": total_tx,
        "paid_tx": paid_tx,
        "status_filter": status_filter,
        "search_query": q,
        "active_tab": "payments",
    }
    return render(request, "admin_payments.html", context)