from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*roles):
    """Allow access only to users whose profile role is in `roles`.
    Admin (role=ADMIN or is_superuser) always passes."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            profile = getattr(request.user, "profile", None)
            if profile and (profile.is_admin or profile.role in roles):
                return view_func(request, *args, **kwargs)
            messages.error(request, "You don't have permission to access that page.")
            return redirect("dashboard")

        return _wrapped

    return decorator


def admin_required(view_func):
    return role_required("ADMIN")(view_func)
