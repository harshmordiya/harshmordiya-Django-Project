from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


def _validate_student_email(student, email_type="notification"):
    """
    Validates that the student object has a valid, non-placeholder email address.
    Returns True if valid, False otherwise.
    Logs clear and safe diagnostic messages to the terminal without crashing.
    """
    if not student:
        print(f"[EMAIL ERROR] Cannot send {email_type} email: Student object is None.")
        return False

    raw_email = getattr(student, "email", None)
    if not raw_email or not str(raw_email).strip():
        student_id = getattr(student, "student_id", "Unknown")
        print(f"[EMAIL ERROR] Cannot send {email_type} email: Student ID {student_id} has no email address configured.")
        return False

    email = str(raw_email).strip()

    # Guard against placeholder email address that causes bounce
    if "YOUR_RECEIVING_EMAIL" in email.upper():
        student_id = getattr(student, "student_id", "Unknown")
        print(f"[EMAIL ERROR] Invalid placeholder recipient email '{email}' detected for Student ID {student_id}. {email_type.capitalize()} email skipped.")
        return False

    try:
        validate_email(email)
    except ValidationError as err:
        student_id = getattr(student, "student_id", "Unknown")
        print(f"[EMAIL ERROR] Invalid email address format '{email}' for Student ID {student_id}: {err}")
        return False

    return True


def send_enrollment_confirmation_email(student, course):
    """
    Sends course enrollment confirmation email to the student after successful enrollment.
    """
    if not _validate_student_email(student, "enrollment confirmation"):
        return False

    course_title = course.title if hasattr(course, "title") else str(course)
    course_category = course.get_category_display() if hasattr(course, "get_category_display") else getattr(course, "category", "General")
    course_duration = getattr(course, "duration", "Self-paced")
    course_price = getattr(course, "price", 0)

    subject = f"Enrollment Successful – {course_title}"
    message = f"""Hello {student.first_name},

Congratulations!
Your enrollment has been successfully confirmed.

Course: {course_title}
Category: {course_category}
Duration: {course_duration}
Course Price: ₹{course_price}

You can now log in to your EduLearn account and access your course in your student dashboard.

Thank you for learning with EduLearn!

Regards,
EduLearn Team
"""

    student_id = getattr(student, "student_id", "Unknown")
    print(f"Sending enrollment confirmation email\nStudent ID: {student_id}\nRecipient: {student.email}\nCourse: {course_title}")

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            fail_silently=False,
        )
        print(f"[EMAIL SUCCESS] Enrollment confirmation email sent successfully to {student.email}")
        return True
    except Exception as exc:
        print(f"[EMAIL ERROR] Failed to send enrollment confirmation email to {student.email}: {exc}")
        raise


def send_payment_confirmation_email(student, payment, course=None):
    """
    Sends payment receipt confirmation email to the student after Razorpay payment verification.
    """
    if not _validate_student_email(student, "payment confirmation"):
        return False

    course_name = course.title if hasattr(course, "title") else (str(course) if course else "EduLearn Course")
    subject = "Payment Successful – EduLearn"
    message = f"""Hello {student.first_name},

Your payment has been successfully received.

Payment Details
----------------
Course: {course_name}
Amount Paid: ₹{payment.amount}
Razorpay Payment ID: {payment.razorpay_payment_id or 'N/A'}
Razorpay Order ID: {payment.razorpay_order_id or 'N/A'}
Payment Status: {payment.status}

Thank you for your payment.

Your enrollment will now be available in your EduLearn account.

Regards,
EduLearn Team
"""

    student_id = getattr(student, "student_id", "Unknown")
    print(f"Sending payment confirmation email\nStudent ID: {student_id}\nRecipient: {student.email}\nCourse: {course_name}")

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            fail_silently=False,
        )
        print(f"[EMAIL SUCCESS] Payment confirmation email sent successfully to {student.email}")
        return True
    except Exception as exc:
        print(f"[EMAIL ERROR] Failed to send payment confirmation email to {student.email}: {exc}")
        raise


def send_course_completion_email(student, course):
    """
    Sends course completion congratulations email to the student when a course is marked completed.
    """
    if not _validate_student_email(student, "course completion"):
        return False

    course_title = course.title if hasattr(course, "title") else str(course)
    course_category = course.get_category_display() if hasattr(course, "get_category_display") else getattr(course, "category", "General")
    course_duration = getattr(course, "duration", "Self-paced")

    subject = "Congratulations! You Completed Your Course 🎉"
    message = f"""Hello {student.first_name},

Congratulations! 🎉

You have successfully completed your course.

Course: {course_title}
Category: {course_category}
Duration: {course_duration}

Thank you for completing your learning journey with EduLearn.

Please log in to your EduLearn account to view your course completion details and certificate, if available.

Keep learning and keep growing!

Regards,
EduLearn Team
"""

    student_id = getattr(student, "student_id", "Unknown")
    print(f"Sending course completion email\nStudent ID: {student_id}\nRecipient: {student.email}\nCourse: {course_title}")

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            fail_silently=False,
        )
        print(f"[EMAIL SUCCESS] Course completion email sent successfully to {student.email}")
        return True
    except Exception as exc:
        print(f"[EMAIL ERROR] Failed to send course completion email to {student.email}: {exc}")
        raise
