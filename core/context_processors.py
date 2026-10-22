from .models import Cart, Course, CourseContent, Enrollment, Student, UserProfile

def site_context(request):
    total_courses = Course.objects.filter(is_active=True).count()
    total_quizzes = CourseContent.objects.filter(content_type="quiz").count()
    total_enrolled = (
        Enrollment.objects
        .filter(status__in=["active", "completed"])
        .values("student")
        .distinct()
        .count()
    )

    context = {
        "nav_cart_count": 0,
        "nav_user_role": None,
        "site_total_courses": total_courses,
        "site_total_quizzes": total_quizzes,
        "site_total_enrolled_students": total_enrolled,
    }
    
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            role = "admin"
            profile = UserProfile.objects.filter(user=request.user).first()
            if not profile:
                UserProfile.objects.create(user=request.user, role="admin")
            elif profile.role != "admin":
                profile.role = "admin"
                profile.save(update_fields=["role"])
        else:
            profile = UserProfile.objects.filter(user=request.user).first()
            if profile:
                role = profile.role
            elif Student.objects.filter(email=request.user.email).exists():
                role = "student"
            else:
                role = "student"

        context["nav_user_role"] = role

        student = Student.objects.filter(email=request.user.email).first()
        if student:
            context["nav_cart_count"] = Cart.objects.filter(student=student).count()
            
    return context
