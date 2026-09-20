from django.conf import settings


def role_flags(request):
    """Expose role booleans and currency code to every template."""
    ctx = {
        "currency_code": getattr(settings, "CURRENCY_CODE", "AED"),
        "is_admin": False,
        "is_requester": False,
        "is_approver1": False,
        "is_approver2": False,
    }
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        profile = getattr(user, "profile", None)
        if profile:
            ctx.update(
                {
                    "is_admin": profile.is_admin,
                    "is_requester": profile.is_requester,
                    "is_approver1": profile.is_approver1,
                    "is_approver2": profile.is_approver2,
                    "user_role_display": profile.get_role_display(),
                }
            )
    return ctx
