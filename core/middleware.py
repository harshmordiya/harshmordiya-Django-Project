from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import redirect


class DeactivatedUserCheckMiddleware:
    """
    Middleware that detects if a session belongs to a user who was
    deactivated by an administrator while logged in.
    Safely flushes their session and redirects them to the login screen
    with a clear explanatory message, preventing 404s or broken redirects.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_user_id = request.session.get("_auth_user_id")
        if session_user_id and (not request.user.is_authenticated):
            try:
                user = User.objects.filter(id=session_user_id).first()
                if user and not user.is_active:
                    request.session.flush()
                    messages.error(
                        request,
                        "Your account has been deactivated by an administrator. You have been signed out."
                    )
                    return redirect("login")
            except Exception:
                pass

        return self.get_response(request)
