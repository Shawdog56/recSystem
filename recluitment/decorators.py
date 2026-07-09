from django.core.exceptions import PermissionDenied

def role_required(allowed_roles=[]):
    def decorator(view_func):
        def wrap(request, *args, **kwargs):
            # Get roles from session
            user_roles = request.session.get('user_roles', [])
            
            # Check if user has at least one of the allowed roles
            if any(role in allowed_roles for role in user_roles):
                return view_func(request, *args, **kwargs)
            else:
                raise PermissionDenied 
        return wrap
    return decorator