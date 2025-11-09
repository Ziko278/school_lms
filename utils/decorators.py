"""
Custom decorators for view access control
"""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def admin_required(view_func):
    """
    Decorator to check if user is admin/superuser
    Usage: @admin_required
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Check if superuser
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Check if user has admin profile type
        if hasattr(request.user, 'profile'):
            if request.user.profile.user_type == 'admin':
                return view_func(request, *args, **kwargs)

        # User is not admin
        messages.error(request, 'You do not have permission to access this page. Admin access required.')
        raise PermissionDenied

    return wrapper


def staff_required(view_func):
    """
    Decorator to check if user is staff/lecturer
    Usage: @staff_required
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Check if user has staff profile
        if hasattr(request.user, 'staff'):
            return view_func(request, *args, **kwargs)

        # Check if user profile type is staff
        if hasattr(request.user, 'profile'):
            if request.user.profile.user_type == 'staff':
                return view_func(request, *args, **kwargs)

        # User is not staff
        messages.error(request, 'You do not have permission to access this page. Staff access required.')

        # Redirect based on user type
        if hasattr(request.user, 'student'):
            return redirect('accounts:student_dashboard')
        elif request.user.is_superuser or (
                hasattr(request.user, 'profile') and request.user.profile.user_type == 'admin'):
            return redirect('admin_site:admin_dashboard')
        else:
            return redirect('accounts:login')

    return wrapper


def lecturer_required(view_func):
    """
    Decorator to check if user is lecturer
    Alias for staff_required since all staff are lecturers in this system
    Usage: @lecturer_required
    """
    return staff_required(view_func)


def student_required(view_func):
    """
    Decorator to check if user is student
    Usage: @student_required
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Check if user has student profile
        if hasattr(request.user, 'student'):
            return view_func(request, *args, **kwargs)

        # Check if user profile type is student
        if hasattr(request.user, 'profile'):
            if request.user.profile.user_type == 'student':
                return view_func(request, *args, **kwargs)

        # User is not student
        messages.error(request, 'You do not have permission to access this page. Student access required.')

        # Redirect based on user type
        if hasattr(request.user, 'staff'):
            return redirect('accounts:staff_dashboard')
        elif request.user.is_superuser or (
                hasattr(request.user, 'profile') and request.user.profile.user_type == 'admin'):
            return redirect('admin_site:admin_dashboard')
        else:
            return redirect('accounts:login')

    return wrapper


def registry_required(view_func):
    """
    Decorator to check if user has registry staff permissions
    Registry staff can verify admissions and approve course registrations
    Usage: @registry_required
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Superusers always have access
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Check if user has registry permissions
        has_admission_perm = request.user.has_perm('admissions.can_verify_student_admission')
        has_course_reg_perm = request.user.has_perm('courses.can_approve_course_registration')
        has_manage_students_perm = request.user.has_perm('accounts.can_manage_students')

        if has_admission_perm or has_course_reg_perm or has_manage_students_perm:
            return view_func(request, *args, **kwargs)

        # User doesn't have registry permissions
        messages.error(request, 'You do not have permission to access this page. Registry staff access required.')
        raise PermissionDenied

    return wrapper


def hod_required(view_func):
    """
    Decorator to check if user is Head of Department (HOD)
    HOD can verify results for their department and allocate courses
    Usage: @hod_required
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Superusers always have access
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Check if user is staff
        if not hasattr(request.user, 'staff'):
            messages.error(request, 'You do not have permission to access this page. HOD access required.')
            raise PermissionDenied

        staff = request.user.staff

        # Check if staff is HOD of any department
        from academics.models import Department
        is_hod = Department.objects.filter(hod=staff).exists()

        if is_hod:
            return view_func(request, *args, **kwargs)

        # Check if user has HOD permissions
        has_verify_results_perm = request.user.has_perm('results.can_verify_results')
        has_allocate_courses_perm = request.user.has_perm('accounts.can_allocate_courses')

        if has_verify_results_perm or has_allocate_courses_perm:
            return view_func(request, *args, **kwargs)

        # User is not HOD
        messages.error(request, 'You do not have permission to access this page. HOD access required.')
        raise PermissionDenied

    return wrapper


def ajax_required(view_func):
    """
    Decorator to check if request is AJAX
    Returns JSON error if not AJAX
    Usage: @ajax_required
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check for AJAX request
        is_ajax = (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                request.headers.get('Accept') == 'application/json' or
                request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        )

        if not is_ajax:
            return JsonResponse({
                'success': False,
                'error': 'This endpoint only accepts AJAX requests'
            }, status=400)

        return view_func(request, *args, **kwargs)

    return wrapper


def permission_required_with_message(permission_codename, message=None):
    """
    Decorator to check specific permission with custom error message
    Usage: @permission_required_with_message('can_verify_results', 'You cannot verify results')
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Superusers always have access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check permission
            if request.user.has_perm(permission_codename):
                return view_func(request, *args, **kwargs)

            # Permission denied
            error_message = message or f'You do not have permission to perform this action.'
            messages.error(request, error_message)
            raise PermissionDenied

        return wrapper

    return decorator


def user_type_required(*allowed_types):
    """
    Decorator to check if user's profile type is in allowed types
    Usage: @user_type_required('admin', 'staff')
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Superusers always have access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check user profile type
            if hasattr(request.user, 'profile'):
                if request.user.profile.user_type in allowed_types:
                    return view_func(request, *args, **kwargs)

            # Check specific user types
            if 'student' in allowed_types and hasattr(request.user, 'student'):
                return view_func(request, *args, **kwargs)

            if 'staff' in allowed_types and hasattr(request.user, 'staff'):
                return view_func(request, *args, **kwargs)

            # User type not allowed
            messages.error(request, 'You do not have permission to access this page.')
            raise PermissionDenied

        return wrapper

    return decorator


def anonymous_required(view_func):
    """
    Decorator to ensure user is NOT logged in (for login/registration pages)
    Redirects logged-in users to their dashboard
    Usage: @anonymous_required
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            # Redirect to appropriate dashboard
            if hasattr(request.user, 'student'):
                return redirect('accounts:student_dashboard')
            elif hasattr(request.user, 'staff'):
                return redirect('accounts:staff_dashboard')
            elif request.user.is_superuser or (
                    hasattr(request.user, 'profile') and request.user.profile.user_type == 'admin'):
                return redirect('admin_site:admin_dashboard')
            else:
                return redirect('accounts:dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper


def ownership_required(model_class, lookup_field='pk', user_field='user'):
    """
    Decorator to check if user owns the object being accessed
    Usage: @ownership_required(Student, 'pk', 'user')

    Args:
        model_class: Model to check ownership of
        lookup_field: URL parameter to lookup object (default: 'pk')
        user_field: Field in model that references user (default: 'user')
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            from django.shortcuts import get_object_or_404

            # Superusers always have access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Get object
            lookup_value = kwargs.get(lookup_field)
            obj = get_object_or_404(model_class, pk=lookup_value)

            # Check ownership
            owner = getattr(obj, user_field)
            if owner == request.user:
                return view_func(request, *args, **kwargs)

            # Not owner
            messages.error(request, 'You do not have permission to access this resource.')
            raise PermissionDenied

        return wrapper

    return decorator


def session_active_required(view_func):
    """
    Decorator to check if there's an active academic session
    Usage: @session_active_required
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        from admin_site.models import SystemSettings

        settings = SystemSettings.get_instance()

        if not settings.current_session:
            messages.warning(request, 'No active academic session. Please contact administrator.')
            return redirect('accounts:dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper


def registration_open_required(view_func):
    """
    Decorator to check if student registration is open
    Usage: @registration_open_required
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from admin_site.models import SystemSettings

        settings = SystemSettings.get_instance()

        if not settings.allow_student_registration:
            messages.warning(request, 'Student registration is currently closed.')
            return redirect('website:home')

        return view_func(request, *args, **kwargs)

    return wrapper


def course_registration_open_required(view_func):
    """
    Decorator to check if course registration is open
    Usage: @course_registration_open_required
    """

    @wraps(view_func)
    @login_required
    @student_required
    def wrapper(request, *args, **kwargs):
        from admin_site.models import SystemSettings

        settings = SystemSettings.get_instance()

        if not settings.allow_course_registration:
            messages.warning(request, 'Course registration is currently closed.')
            return redirect('accounts:student_dashboard')

        return view_func(request, *args, **kwargs)

    return wrapper


# Combination decorators for common use cases
def admin_or_registry_required(view_func):
    """
    Decorator for views that can be accessed by admin OR registry staff
    Usage: @admin_or_registry_required
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Check if admin
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        if hasattr(request.user, 'profile') and request.user.profile.user_type == 'admin':
            return view_func(request, *args, **kwargs)

        # Check registry permissions
        has_registry_perm = (
                request.user.has_perm('admissions.can_verify_student_admission') or
                request.user.has_perm('courses.can_approve_course_registration') or
                request.user.has_perm('accounts.can_manage_students')
        )

        if has_registry_perm:
            return view_func(request, *args, **kwargs)

        messages.error(request, 'You do not have permission to access this page.')
        raise PermissionDenied

    return wrapper


def admin_or_hod_required(view_func):
    """
    Decorator for views that can be accessed by admin OR HOD
    Usage: @admin_or_hod_required
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Check if admin
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        if hasattr(request.user, 'profile') and request.user.profile.user_type == 'admin':
            return view_func(request, *args, **kwargs)

        # Check if HOD
        if hasattr(request.user, 'staff'):
            from academics.models import Department
            is_hod = Department.objects.filter(hod=request.user.staff).exists()

            if is_hod or request.user.has_perm('results.can_verify_results'):
                return view_func(request, *args, **kwargs)

        messages.error(request, 'You do not have permission to access this page.')
        raise PermissionDenied

    return wrapper