import random 
import razorpay

from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings

# Create your views here.

from .forms import RegistrationForm
from .models import Cart, Course, PasswordResetOTP ,Student,UserProfile


razorpay_client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    )
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
    course = get_object_or_404(
        Course,
        course_id=course_id,
        is_active=True
    )

    return render(
        request,
        "course_detail.html",
        {
            "course": course
        }
    )

@login_required
def add_to_cart(request, course_id):

    course = get_object_or_404(
        Course,
        course_id=course_id,
        is_active=True
    )

    student = Student.objects.filter(
        email=request.user.email
    ).first()

    if not student:
        messages.error(
            request,
            "No student profile found for this account."
        )

        return redirect("course_detail", course_id=course_id)

    cart_item, created = Cart.objects.get_or_create(
        student=student,
        course=course
    )

    if created:
        messages.success(
            request,
            "Course added to cart successfully!"
        )
    else:
        messages.info(
            request,
            "This course is already in your cart."
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
        return redirect("course_list")

    cart_items = Cart.objects.filter(
        student=student
    ).select_related("course")

    return render(
        request,
        "cart.html",
        {
            "cart_items": cart_items
        }
    )