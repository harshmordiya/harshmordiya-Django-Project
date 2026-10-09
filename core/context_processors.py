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
        # Determine user role
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile:
            context["nav_user_role"] = profile.role
        
        # Calculate cart items for students
        student = Student.objects.filter(email=request.user.email).first()
        if student:
            context["nav_cart_count"] = Cart.objects.filter(student=student).count()
            
    return context
