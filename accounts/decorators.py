from django.core.exceptions import PermissionDenied
from functools import wraps


def role_required(*roles):
    """
    Decorator that restricts a view to users with specific roles.
    Usage: @role_required('teacher', 'class_master')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            # allow superusers and staff to bypass role restrictions
            if getattr(request.user, 'is_superuser', False) or getattr(request.user, 'is_staff', False):
                return view_func(request, *args, **kwargs)
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator