from .models import Cart, Student, UserProfile

def site_context(request):
    """
    Context processor to supply global context for the navigation bar
    and layout, including cart count and user role.
    """
    context = {
        "nav_cart_count": 0,
        "nav_user_role": None,
    }
    
    if request.user.is_authenticated:
        # Determine user role accurately
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

        # Calculate cart items for students
        student = Student.objects.filter(email=request.user.email).first()
        if student:
            context["nav_cart_count"] = Cart.objects.filter(student=student).count()
            
    return context
