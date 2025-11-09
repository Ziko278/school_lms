from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta

from .models import UserProfile, Staff, Student, ChangePasswordRequest
from .forms import (
    UserLoginForm, UserProfileForm, StaffCreationForm, StaffEditForm,
    StudentEditForm, ChangePasswordRequestForm, CustomPasswordChangeForm
)
from academics.models import Session, Department, Level
from courses.models import CourseRegistration, CourseAllocation
from results.models import Result
from attendance.models import AttendanceRecord
from utils.decorators import admin_required, staff_required, student_required


# ========================== AUTHENTICATION VIEWS ==========================

def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)

                # Check if first login (password change required)
                if hasattr(user, 'student'):
                    student = user.student
                    # Check if password is still default (username)
                    if user.check_password(student.matric_number):
                        messages.warning(request, 'Please change your default password.')
                        return redirect('accounts:change_password')

                messages.success(request, f'Welcome back, {user.get_full_name()}!')

                # Redirect based on user type
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)

                return redirect('accounts:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()

    context = {
        'form': form,
        'title': 'Login'
    }
    return render(request, 'accounts/login.html', context)


@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


# ========================== DASHBOARD VIEWS ==========================

@login_required
def dashboard_view(request):
    """Main dashboard - redirects to appropriate dashboard based on user type"""
    user = request.user

    # Check user type and redirect to appropriate dashboard
    if user.is_superuser or (hasattr(user, 'profile') and user.profile.user_type == 'admin'):
        return redirect('admin_site:admin_dashboard')
    elif hasattr(user, 'staff'):
        return staff_dashboard_view(request)
    elif hasattr(user, 'student'):
        return student_dashboard_view(request)
    else:
        messages.error(request, 'User profile not properly configured.')
        return redirect('accounts:login')


@login_required
@staff_required
def staff_dashboard_view(request):
    """Staff/Lecturer dashboard"""
    staff = request.user.staff

    # Get allocated courses for current session/semester
    from admin_site.models import SystemSettings
    settings = SystemSettings.get_instance()
    current_session = settings.current_session
    current_semester = settings.current_semester

    allocated_courses = CourseAllocation.objects.filter(
        lecturer=staff,
        session=current_session,
        semester=current_semester
    ).select_related('course', 'session', 'semester')

    # Get statistics
    total_students = 0
    for allocation in allocated_courses:
        total_students += CourseRegistration.objects.filter(
            course=allocation.course,
            session=current_session,
            semester=current_semester,
            status='approved'
        ).count()

    # Get pending results to submit
    from materials.models import Assignment, AssignmentSubmission
    pending_assignments = AssignmentSubmission.objects.filter(
        assignment__course_allocation__lecturer=staff,
        score__isnull=True
    ).select_related('assignment', 'student').count()

    # Recent activities
    recent_submissions = AssignmentSubmission.objects.filter(
        assignment__course_allocation__lecturer=staff
    ).select_related('assignment', 'student').order_by('-submitted_at')[:5]

    context = {
        'title': 'Staff Dashboard',
        'staff': staff,
        'allocated_courses': allocated_courses,
        'total_courses': allocated_courses.count(),
        'total_students': total_students,
        'pending_assignments': pending_assignments,
        'recent_submissions': recent_submissions,
        'current_session': current_session,
        'current_semester': current_semester,
    }
    return render(request, 'accounts/staff_dashboard.html', context)


@login_required
@student_required
def student_dashboard_view(request):
    """Student dashboard"""
    student = request.user.student

    # Get current session/semester
    from admin_site.models import SystemSettings
    settings = SystemSettings.get_instance()
    current_session = settings.current_session
    current_semester = settings.current_semester

    # Get registered courses
    registered_courses = CourseRegistration.objects.filter(
        student=student,
        session=current_session,
        semester=current_semester,
        status='approved'
    ).select_related('course')

    # Get pending assignments
    from materials.models import Assignment, AssignmentSubmission
    pending_assignments = []
    for reg in registered_courses:
        course_assignments = Assignment.objects.filter(
            course_allocation__course=reg.course,
            course_allocation__session=current_session,
            course_allocation__semester=current_semester,
            due_date__gte=timezone.now()
        ).exclude(
            submissions__student=student
        )
        pending_assignments.extend(course_assignments)

    # Get attendance summary
    total_classes = AttendanceRecord.objects.filter(
        student=student,
        attendance__course_allocation__session=current_session,
        attendance__course_allocation__semester=current_semester
    ).count()

    present_classes = AttendanceRecord.objects.filter(
        student=student,
        status='present',
        attendance__course_allocation__session=current_session,
        attendance__course_allocation__semester=current_semester
    ).count()

    attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0

    # Get latest results
    latest_results = Result.objects.filter(
        student=student,
        status='verified'
    ).select_related('course', 'session', 'semester').order_by('-submitted_at')[:5]

    # Calculate current semester GPA
    semester_results = Result.objects.filter(
        student=student,
        session=current_session,
        semester=current_semester,
        status='verified'
    ).select_related('course')

    from utils.helpers import calculate_gpa, calculate_cgpa
    current_gpa = calculate_gpa(semester_results) if semester_results else 0.0
    cgpa = calculate_cgpa(student)

    context = {
        'title': 'Student Dashboard',
        'student': student,
        'registered_courses': registered_courses,
        'total_courses': registered_courses.count(),
        'pending_assignments': pending_assignments[:5],
        'total_pending_assignments': len(pending_assignments),
        'attendance_percentage': round(attendance_percentage, 2),
        'total_classes': total_classes,
        'present_classes': present_classes,
        'latest_results': latest_results,
        'current_gpa': current_gpa,
        'cgpa': cgpa,
        'current_session': current_session,
        'current_semester': current_semester,
    }
    return render(request, 'accounts/student_dashboard.html', context)


# ========================== PROFILE VIEWS ==========================

@login_required
def profile_view(request):
    """View and edit user profile"""
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=profile)

    context = {
        'title': 'My Profile',
        'form': form,
        'profile': profile,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def change_password_view(request):
    """Change password view"""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(request.user)

    context = {
        'title': 'Change Password',
        'form': form,
    }
    return render(request, 'accounts/change_password.html', context)


@login_required
@student_required
def request_password_change_view(request):
    """Student request for password change"""
    if request.method == 'POST':
        form = ChangePasswordRequestForm(request.POST)
        if form.is_valid():
            password_request = form.save(commit=False)
            password_request.user = request.user
            password_request.save()
            messages.success(request,
                             'Your password change request has been submitted. You will be notified once processed.')
            return redirect('accounts:dashboard')
    else:
        form = ChangePasswordRequestForm()

    context = {
        'title': 'Request Password Change',
        'form': form,
    }
    return render(request, 'accounts/request_password_change.html', context)


# ========================== STAFF MANAGEMENT VIEWS ==========================

@login_required
@admin_required
def staff_list_view(request):
    """List all staff members"""
    staff_list = Staff.objects.select_related(
        'user', 'user__profile', 'department'
    ).all()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        staff_list = staff_list.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(staff_id__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    # Filter by department
    department_id = request.GET.get('department', '')
    if department_id:
        staff_list = staff_list.filter(department_id=department_id)

    # Pagination
    paginator = Paginator(staff_list, 20)
    page_number = request.GET.get('page')
    staff_page = paginator.get_page(page_number)

    departments = Department.objects.all()

    context = {
        'title': 'Staff List',
        'staff_page': staff_page,
        'departments': departments,
        'search_query': search_query,
        'selected_department': department_id,
    }
    return render(request, 'accounts/staff_list.html', context)


@login_required
@admin_required
def staff_create_view(request):
    """Create new staff member"""
    if request.method == 'POST':
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            staff = form.save()

            # Generate staff ID
            from utils.helpers import generate_staff_id
            staff.staff_id = generate_staff_id(staff)
            staff.save()

            # Assign to Staff group
            from django.contrib.auth.models import Group
            staff_group, created = Group.objects.get_or_create(name='Staff')
            staff.user.groups.add(staff_group)

            messages.success(request, f'Staff member {staff.user.get_full_name()} created successfully!')
            return redirect('accounts:staff_list')
    else:
        form = StaffCreationForm()

    context = {
        'title': 'Create Staff',
        'form': form,
    }
    return render(request, 'accounts/staff_form.html', context)


@login_required
@admin_required
def staff_edit_view(request, pk):
    """Edit staff details"""
    staff = get_object_or_404(Staff, pk=pk)

    if request.method == 'POST':
        form = StaffEditForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff details updated successfully!')
            return redirect('accounts:staff_detail', pk=pk)
    else:
        form = StaffEditForm(instance=staff)

    context = {
        'title': 'Edit Staff',
        'form': form,
        'staff': staff,
    }
    return render(request, 'accounts/staff_form.html', context)


@login_required
@admin_required
def staff_detail_view(request, pk):
    """View staff details"""
    staff = get_object_or_404(
        Staff.objects.select_related('user', 'user__profile', 'department'),
        pk=pk
    )

    # Get allocated courses
    allocated_courses = CourseAllocation.objects.filter(
        lecturer=staff
    ).select_related('course', 'session', 'semester').order_by('-session')[:10]

    context = {
        'title': f'Staff Details - {staff.user.get_full_name()}',
        'staff': staff,
        'allocated_courses': allocated_courses,
    }
    return render(request, 'accounts/staff_detail.html', context)


@login_required
@admin_required
def staff_delete_view(request, pk):
    """Delete staff member"""
    staff = get_object_or_404(Staff, pk=pk)

    if request.method == 'POST':
        user = staff.user
        staff_name = user.get_full_name()

        # Delete staff and user
        staff.delete()
        user.delete()

        messages.success(request, f'Staff member {staff_name} deleted successfully!')
        return redirect('accounts:staff_list')

    context = {
        'title': 'Delete Staff',
        'staff': staff,
    }
    return render(request, 'accounts/staff_confirm_delete.html', context)


# ========================== STUDENT MANAGEMENT VIEWS ==========================

@login_required
@admin_required
def student_list_view(request):
    """List all students"""
    students = Student.objects.select_related(
        'user', 'user__profile', 'department', 'program', 'current_level', 'admission_session'
    ).all()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        students = students.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(matric_number__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    # Filters
    department_id = request.GET.get('department', '')
    if department_id:
        students = students.filter(department_id=department_id)

    level_id = request.GET.get('level', '')
    if level_id:
        students = students.filter(current_level_id=level_id)

    status = request.GET.get('status', '')
    if status:
        students = students.filter(admission_status=status)

    # Pagination
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    students_page = paginator.get_page(page_number)

    departments = Department.objects.all()
    levels = Level.objects.all()

    context = {
        'title': 'Student List',
        'students_page': students_page,
        'departments': departments,
        'levels': levels,
        'search_query': search_query,
        'selected_department': department_id,
        'selected_level': level_id,
        'selected_status': status,
        'status_choices': Student.STATUS_CHOICES,
    }
    return render(request, 'accounts/student_list.html', context)


@login_required
@admin_required
def student_detail_view(request, pk):
    """View student details"""
    student = get_object_or_404(
        Student.objects.select_related(
            'user', 'user__profile', 'department', 'program',
            'current_level', 'admission_session'
        ),
        pk=pk
    )

    # Get enrolled courses (current semester)
    from admin_site.models import SystemSettings
    settings = SystemSettings.get_instance()

    enrolled_courses = CourseRegistration.objects.filter(
        student=student,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    # Get all results
    all_results = Result.objects.filter(
        student=student,
        status='verified'
    ).select_related('course', 'session', 'semester').order_by('-session', '-semester')

    # Calculate CGPA
    from utils.helpers import calculate_cgpa
    cgpa = calculate_cgpa(student)

    # Get attendance summary
    total_classes = AttendanceRecord.objects.filter(student=student).count()
    present_classes = AttendanceRecord.objects.filter(student=student, status='present').count()
    attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0

    context = {
        'title': f'Student Details - {student.user.get_full_name()}',
        'student': student,
        'enrolled_courses': enrolled_courses,
        'all_results': all_results[:10],  # Show recent 10
        'cgpa': cgpa,
        'attendance_percentage': round(attendance_percentage, 2),
        'total_classes': total_classes,
    }
    return render(request, 'accounts/student_detail.html', context)


@login_required
@admin_required
def student_edit_view(request, pk):
    """Edit student details"""
    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student details updated successfully!')
            return redirect('accounts:student_detail', pk=pk)
    else:
        form = StudentEditForm(instance=student)

    context = {
        'title': 'Edit Student',
        'form': form,
        'student': student,
    }
    return render(request, 'accounts/student_form.html', context)


# ========================== PASSWORD REQUEST MANAGEMENT ==========================

@login_required
@admin_required
def password_request_list_view(request):
    """List all password change requests"""
    requests_list = ChangePasswordRequest.objects.select_related(
        'user', 'processed_by'
    ).all()

    # Filter by status
    status = request.GET.get('status', '')
    if status:
        requests_list = requests_list.filter(status=status)
    else:
        # Show pending by default
        requests_list = requests_list.filter(status='pending')

    # Pagination
    paginator = Paginator(requests_list, 20)
    page_number = request.GET.get('page')
    requests_page = paginator.get_page(page_number)

    context = {
        'title': 'Password Change Requests',
        'requests_page': requests_page,
        'selected_status': status,
        'status_choices': ChangePasswordRequest.STATUS_CHOICES,
    }
    return render(request, 'accounts/password_request_list.html', context)


@login_required
@admin_required
def password_request_approve_view(request, pk):
    """Approve password change request"""
    if request.method == 'POST':
        password_request = get_object_or_404(ChangePasswordRequest, pk=pk)

        # Generate new random password
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        new_password = ''.join(secrets.choice(alphabet) for i in range(10))

        # Update user password
        user = password_request.user
        user.set_password(new_password)
        user.save()

        # Update request
        password_request.status = 'approved'
        password_request.processed_by = request.user
        password_request.processed_at = timezone.now()
        password_request.save()

        # Send email with new password
        from django.core.mail import send_mail
        from admin_site.models import SchoolInfo
        school_info = SchoolInfo.get_instance()

        send_mail(
            f'Password Reset - {school_info.school_name}',
            f'Hello {user.get_full_name()},\n\nYour password has been reset.\n\nNew Password: {new_password}\n\nPlease login and change your password immediately.\n\nBest regards,\n{school_info.school_name}',
            None,
            [user.email],
            fail_silently=False,
        )

        messages.success(request, f'Password changed and sent to {user.email}')
        return redirect('accounts:password_request_list')

    return redirect('accounts:password_request_list')


@login_required
@admin_required
def password_request_reject_view(request, pk):
    """Reject password change request"""
    if request.method == 'POST':
        password_request = get_object_or_404(ChangePasswordRequest, pk=pk)

        password_request.status = 'rejected'
        password_request.processed_by = request.user
        password_request.processed_at = timezone.now()
        password_request.save()

        messages.success(request, 'Password change request rejected.')
        return redirect('accounts:password_request_list')

    return redirect('accounts:password_request_list')


# ========================== AJAX VIEWS ==========================

@require_http_methods(["GET"])
def check_username_ajax(request):
    """Check if username exists"""
    username = request.GET.get('username', '')
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({'exists': exists})


@require_http_methods(["GET"])
def check_email_ajax(request):
    """Check if email exists"""
    email = request.GET.get('email', '')
    exists = User.objects.filter(email=email).exists()
    return JsonResponse({'exists': exists})


@login_required
@require_http_methods(["POST"])
def update_profile_picture_ajax(request):
    """Update profile picture via AJAX"""
    try:
        profile = request.user.profile
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()

            return JsonResponse({
                'success': True,
                'image_url': profile.profile_picture.url
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No image file provided'
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@admin_required
@require_http_methods(["GET"])
def staff_search_ajax(request):
    """Search staff by name or ID"""
    query = request.GET.get('q', '')

    if len(query) < 2:
        return JsonResponse({'results': []})

    staff_list = Staff.objects.filter(
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(staff_id__icontains=query)
    ).select_related('user')[:10]

    results = [{
        'id': staff.id,
        'staff_id': staff.staff_id,
        'name': staff.user.get_full_name(),
        'email': staff.user.email,
        'department': staff.department.name if staff.department else 'N/A'
    } for staff in staff_list]

    return JsonResponse({'results': results})


@login_required
@admin_required
@require_http_methods(["GET"])
def student_search_ajax(request):
    """Search student by matric number or name"""
    query = request.GET.get('q', '')

    if len(query) < 2:
        return JsonResponse({'results': []})

    students = Student.objects.filter(
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(matric_number__icontains=query)
    ).select_related('user', 'department', 'current_level')[:10]

    results = [{
        'id': student.id,
        'matric_number': student.matric_number,
        'name': student.user.get_full_name(),
        'email': student.user.email,
        'department': student.department.name,
        'level': student.current_level.name
    } for student in students]

    return JsonResponse({'results': results})


@login_required
@admin_required
@require_http_methods(["POST"])
def bulk_staff_action_ajax(request):
    """Perform bulk actions on staff"""
    try:
        action = request.POST.get('action')
        staff_ids = request.POST.getlist('staff_ids[]')

        if not staff_ids:
            return JsonResponse({
                'success': False,
                'message': 'No staff members selected'
            }, status=400)

        if action == 'activate':
            Staff.objects.filter(id__in=staff_ids).update(user__is_active=True)
            message = f'{len(staff_ids)} staff member(s) activated'
        elif action == 'deactivate':
            Staff.objects.filter(id__in=staff_ids).update(user__is_active=False)
            message = f'{len(staff_ids)} staff member(s) deactivated'
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid action'
            }, status=400)

        return JsonResponse({
            'success': True,
            'message': message
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    