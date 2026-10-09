import random 
import razorpay

from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
from functools import wraps
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# Create your views here.

from .forms import RegistrationForm, CourseForm, CourseContentForm
from .models import Cart, Course, CourseContent, PasswordResetOTP, Student, UserProfile, Payment, Enrollment, Instructor


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
            form.save()
            return redirect("login")

    else:
        form = RegistrationForm()

    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        return render(
            request,
            "login.html",
            {"error": "Invalid username or password."}
        )

    return render(request, "login.html")


@login_required
def dashboard_view(request):
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"role": "student"}
    )

    return render(
        request,
        "dashboard.html",
        {
            "profile": profile
        }
    )


def logout_view(request):
    logout(request)
    return redirect("login")

def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
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

        send_mail(
            subject="Password Reset OTP",
            message=f"Your password reset OTP is: {otp}",
            from_email="noreply@example.com",
            recipient_list=[email],
        )

        request.session["reset_email"] = email

        return redirect("verify_otp")

    return render(request, "forgot_password.html")

def verify_otp_view(request):
    email = request.session.get("reset_email")

    if not email:
        return redirect("forgot_password")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        try:
            user = User.objects.get(email=email)
            otp_record = PasswordResetOTP.objects.filter(
                user=user,
                otp=entered_otp,
                is_verified=False
            ).latest("created_at")

        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
            return render(
                request,
                "verify_otp.html",
                {"error": "Invalid OTP."}
            )

        # OTP expires after 5 minutes
        elapsed_time = timezone.now() - otp_record.created_at

        if elapsed_time.total_seconds() > 300:
            otp_record.delete()

            return render(
                request,
                "verify_otp.html",
                {"error": "OTP has expired. Please request a new OTP."}
            )

        otp_record.is_verified = True
        otp_record.save()

        request.session["otp_verified"] = True

        return redirect("reset_password")

    return render(request, "verify_otp.html")

def reset_password_view(request):
    email = request.session.get("reset_email")
    otp_verified = request.session.get("otp_verified")

    if not email or not otp_verified:
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(
                request,
                "reset_password.html",
                {"error": "Passwords do not match."}
            )

        if len(password) < 8:
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

        student = Student.objects.filter(email=request.user.email).first()
        if student:
            is_enrolled = Enrollment.objects.filter(student=student, course=course, status="active").exists()

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

@login_required
def add_to_cart(request, course_id):

    student = Student.objects.filter(
        email=request.user.email
    ).first()

    if not student:
        messages.error(
            request,
            "No student profile found for this account."
        )
        return redirect("course_list")

    course = get_object_or_404(
        Course,
        course_id=course_id
    )

    cart_item, created = Cart.objects.get_or_create(
        student=student,
        course=course
    )

    if created:
        messages.success(
            request,
            f"{course.title} added to your cart."
        )
    else:
        messages.info(
            request,
            f"{course.title} is already in your cart."
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

    cart_item = get_object_or_404(
        Cart,
        cart_id=cart_id,
        student=student
    )

    cart_item.delete()

    messages.success(
        request,
        "Course removed from cart."
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

    student = Student.objects.filter(
        email=request.user.email
    ).first()

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

    student = Student.objects.filter(
        email=request.user.email
    ).first()

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
            filter=Q(enrollments__status="active")
        ),
        total_enrollments_count=Count("enrollments")
    ).order_by("-created_at")

    total_courses = courses.count()
    active_courses = courses.filter(is_active=True).count()
    inactive_courses = total_courses - active_courses

    # Real enrollment metrics across all courses by this instructor
    total_enrollments = Enrollment.objects.filter(
        course__instructor=instructor,
        status="active"
    ).count()

    unique_students = Enrollment.objects.filter(
        course__instructor=instructor,
        status="active"
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
    - Instructors can manage courses that belong to them (or unclaimed courses).
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
        if instructor and (course.instructor == instructor or course.instructor is None):
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

    enrolled_count = course.enrollments.filter(status="active").count()

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
    return render(
        request,
        "course_content_manage.html",
        {
            "course": course,
            "contents": contents,
            "instructor": course.instructor or instructor,
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
        form = CourseContentForm(request.POST)
        if form.is_valid():
            content = form.save(commit=False)
            content.course = course
            content.save()
            messages.success(request, f'Lesson "{content.title}" was added successfully!')
            return redirect("course_content_manage", course_id=course.course_id)
    else:
        next_order = course.contents.count() + 1
        form = CourseContentForm(initial={"order": next_order})

    return render(
        request,
        "course_content_form.html",
        {
            "form": form,
            "course": course,
            "title": f"Add Lesson: {course.title}",
            "subtitle": "Add lecture video link, study documents, reading notes, or assignments.",
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
        form = CourseContentForm(request.POST, instance=content)
        if form.is_valid():
            form.save()
            messages.success(request, f'Lesson "{content.title}" updated successfully!')
            return redirect("course_content_manage", course_id=course.course_id)
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