from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone

from .models import Course, CourseAllocation, CourseRegistration
from .forms import (
    CourseForm, CourseAllocationForm, BulkCourseAllocationForm,
    CourseRegistrationForm, CourseRegistrationApprovalForm
)
from academics.models import Department, Level, Session, Semester
from accounts.models import Staff, Student
from admin_site.models import SystemSettings
from utils.decorators import admin_required, staff_required, student_required


# ========================== COURSE MANAGEMENT VIEWS ==========================

@login_required
@admin_required
def course_list_view(request):
    """List all courses"""
    courses = Course.objects.select_related('department', 'level').all()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        courses = courses.filter(
            Q(code__icontains=search_query) |
            Q(title__icontains=search_query)
        )

    # Filters
    department_id = request.GET.get('department', '')
    if department_id:
        courses = courses.filter(department_id=department_id)

    level_id = request.GET.get('level', '')
    if level_id:
        courses = courses.filter(level_id=level_id)

    semester = request.GET.get('semester', '')
    if semester:
        courses = courses.filter(semester_offered=semester)

    # Pagination
    paginator = Paginator(courses, 20)
    page_number = request.GET.get('page')
    courses_page = paginator.get_page(page_number)

    departments = Department.objects.all()
    levels = Level.objects.all()

    context = {
        'title': 'Courses',
        'courses_page': courses_page,
        'departments': departments,
        'levels': levels,
        'search_query': search_query,
        'selected_department': department_id,
        'selected_level': level_id,
        'selected_semester': semester,
        'semester_choices': Course.SEMESTER_CHOICES,
    }
    return render(request, 'courses/course_list.html', context)


@login_required
@admin_required
def course_create_view(request):
    """Create new course"""
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, f'Course {course.code} - {course.title} created successfully!')
            return redirect('courses:course_list')
    else:
        form = CourseForm()

    context = {
        'title': 'Create Course',
        'form': form,
    }
    return render(request, 'courses/course_form.html', context)


@login_required
@admin_required
def course_edit_view(request, pk):
    """Edit course"""
    course = get_object_or_404(Course, pk=pk)

    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f'Course {course.code} updated successfully!')
            return redirect('courses:course_detail', pk=pk)
    else:
        form = CourseForm(instance=course)

    context = {
        'title': 'Edit Course',
        'form': form,
        'course': course,
    }
    return render(request, 'courses/course_form.html', context)


@login_required
@admin_required
def course_detail_view(request, pk):
    """View course details"""
    course = get_object_or_404(
        Course.objects.select_related('department', 'level'),
        pk=pk
    )

    # Get current allocations
    settings = SystemSettings.get_instance()
    current_allocations = CourseAllocation.objects.filter(
        course=course
    ).select_related('lecturer__user', 'session', 'semester').order_by('-session')[:5]

    # Get registered students count
    registered_count = CourseRegistration.objects.filter(
        course=course,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).count()

    # Get prerequisites
    prerequisites = course.prerequisites.all()

    # Get courses that require this as prerequisite
    required_for = course.required_for.all()

    context = {
        'title': f'{course.code} - {course.title}',
        'course': course,
        'current_allocations': current_allocations,
        'registered_count': registered_count,
        'prerequisites': prerequisites,
        'required_for': required_for,
    }
    return render(request, 'courses/course_detail.html', context)


@login_required
@admin_required
def course_delete_view(request, pk):
    """Delete course"""
    course = get_object_or_404(Course, pk=pk)

    if request.method == 'POST':
        # Check if course has dependencies
        if course.registrations.exists():
            messages.error(request, 'Cannot delete course with existing registrations.')
            return redirect('courses:course_list')

        course_code = course.code
        course.delete()
        messages.success(request, f'Course {course_code} deleted successfully!')
        return redirect('courses:course_list')

    context = {
        'title': 'Delete Course',
        'course': course,
    }
    return render(request, 'courses/course_confirm_delete.html', context)


# ========================== COURSE ALLOCATION VIEWS ==========================

@login_required
@admin_required
def course_allocation_list_view(request):
    """List all course allocations"""
    allocations = CourseAllocation.objects.select_related(
        'course', 'lecturer__user', 'session', 'semester'
    ).all().order_by('-session', '-semester', 'course__code')

    # Filters
    session_id = request.GET.get('session', '')
    if session_id:
        allocations = allocations.filter(session_id=session_id)

    semester_id = request.GET.get('semester', '')
    if semester_id:
        allocations = allocations.filter(semester_id=semester_id)

    department_id = request.GET.get('department', '')
    if department_id:
        allocations = allocations.filter(course__department_id=department_id)

    lecturer_id = request.GET.get('lecturer', '')
    if lecturer_id:
        allocations = allocations.filter(lecturer_id=lecturer_id)

    # Pagination
    paginator = Paginator(allocations, 20)
    page_number = request.GET.get('page')
    allocations_page = paginator.get_page(page_number)

    sessions = Session.objects.all()
    semesters = Semester.objects.all()
    departments = Department.objects.all()
    lecturers = Staff.objects.select_related('user').all()

    context = {
        'title': 'Course Allocations',
        'allocations_page': allocations_page,
        'sessions': sessions,
        'semesters': semesters,
        'departments': departments,
        'lecturers': lecturers,
        'selected_session': session_id,
        'selected_semester': semester_id,
        'selected_department': department_id,
        'selected_lecturer': lecturer_id,
    }
    return render(request, 'courses/allocation_list.html', context)


@login_required
@admin_required
def course_allocation_create_view(request):
    """Create new course allocation"""
    if request.method == 'POST':
        form = CourseAllocationForm(request.POST)
        if form.is_valid():
            allocation = form.save()
            messages.success(request,
                             f'Course {allocation.course.code} allocated to {allocation.lecturer.user.get_full_name()} successfully!')
            return redirect('courses:allocation_list')
    else:
        form = CourseAllocationForm()

    departments = Department.objects.all()  # Add this line

    context = {
        'title': 'Allocate Course',
        'form': form,
        'departments': departments,  # Add this line
    }
    return render(request, 'courses/allocation_form.html', context)

@login_required
@admin_required
def course_allocation_bulk_view(request):
    """Bulk course allocation interface"""
    if request.method == 'POST':
        # Handle bulk allocation submission
        session_id = request.POST.get('session')
        semester_id = request.POST.get('semester')

        session = get_object_or_404(Session, id=session_id)
        semester = get_object_or_404(Semester, id=semester_id)

        allocated_count = 0

        # Process each course-lecturer pair
        for key, value in request.POST.items():
            if key.startswith('lecturer_'):
                course_id = key.replace('lecturer_', '')
                lecturer_id = value

                if course_id and lecturer_id:
                    try:
                        course = Course.objects.get(id=course_id)
                        lecturer = Staff.objects.get(id=lecturer_id)

                        # Check if allocation already exists
                        allocation, created = CourseAllocation.objects.get_or_create(
                            course=course,
                            session=session,
                            semester=semester,
                            defaults={'lecturer': lecturer}
                        )

                        if created:
                            allocated_count += 1
                        elif allocation.lecturer != lecturer:
                            allocation.lecturer = lecturer
                            allocation.save()
                            allocated_count += 1
                    except (Course.DoesNotExist, Staff.DoesNotExist):
                        continue

        messages.success(request, f'{allocated_count} course(s) allocated successfully!')
        return redirect('courses:allocation_list')
    else:
        form = BulkCourseAllocationForm()

    context = {
        'title': 'Bulk Course Allocation',
        'form': form,
    }
    return render(request, 'courses/allocation_bulk.html', context)


@login_required
@admin_required
def course_allocation_delete_view(request, pk):
    """Delete course allocation"""
    if request.method == 'POST':
        allocation = get_object_or_404(CourseAllocation, pk=pk)
        course_code = allocation.course.code
        allocation.delete()
        messages.success(request, f'Allocation for {course_code} removed successfully!')

    return redirect('courses:allocation_list')


# ========================== COURSE REGISTRATION MANAGEMENT ==========================

@login_required
@admin_required
def course_registration_list_view(request):
    """List all course registrations (Admin/Registry view)"""
    registrations = CourseRegistration.objects.select_related(
        'student__user', 'student__department', 'student__current_level',
        'course', 'session', 'semester'
    ).all().order_by('-registration_date')

    # Filters
    status = request.GET.get('status', '')
    if status:
        registrations = registrations.filter(status=status)
    else:
        # Show pending by default
        registrations = registrations.filter(status='pending')

    department_id = request.GET.get('department', '')
    if department_id:
        registrations = registrations.filter(student__department_id=department_id)

    session_id = request.GET.get('session', '')
    if session_id:
        registrations = registrations.filter(session_id=session_id)

    semester_id = request.GET.get('semester', '')
    if semester_id:
        registrations = registrations.filter(semester_id=semester_id)

    # Search by matric number
    search_query = request.GET.get('search', '')
    if search_query:
        registrations = registrations.filter(
            student__matric_number__icontains=search_query
        )

    # Pagination
    paginator = Paginator(registrations, 20)
    page_number = request.GET.get('page')
    registrations_page = paginator.get_page(page_number)

    departments = Department.objects.all()
    sessions = Session.objects.all()
    semesters = Semester.objects.all()

    context = {
        'title': 'Course Registrations',
        'registrations_page': registrations_page,
        'departments': departments,
        'sessions': sessions,
        'semesters': semesters,
        'selected_status': status,
        'selected_department': department_id,
        'selected_session': session_id,
        'selected_semester': semester_id,
        'search_query': search_query,
        'status_choices': CourseRegistration.STATUS_CHOICES,
    }
    return render(request, 'courses/registration_list.html', context)


@login_required
@admin_required
def course_registration_approve_view(request, pk):
    """Approve single course registration"""
    if request.method == 'POST':
        registration = get_object_or_404(CourseRegistration, pk=pk)
        registration.status = 'approved'
        registration.save()
        messages.success(request, f'Registration approved for {registration.student.matric_number}')

    return redirect('courses:registration_list')


@login_required
@admin_required
def course_registration_reject_view(request, pk):
    """Reject single course registration"""
    if request.method == 'POST':
        registration = get_object_or_404(CourseRegistration, pk=pk)
        registration.status = 'rejected'
        registration.save()
        messages.success(request, f'Registration rejected for {registration.student.matric_number}')

    return redirect('courses:registration_list')


@login_required
@admin_required
def course_registration_bulk_approve_view(request):
    """Bulk approve course registrations"""
    if request.method == 'POST':
        registration_ids = request.POST.getlist('registration_ids')

        if registration_ids:
            CourseRegistration.objects.filter(
                id__in=registration_ids
            ).update(status='approved')

            messages.success(request, f'{len(registration_ids)} registration(s) approved successfully!')
        else:
            messages.warning(request, 'No registrations selected.')

    return redirect('courses:registration_list')


# ========================== STUDENT COURSE REGISTRATION VIEWS ==========================

@login_required
@student_required
def student_course_registration_view(request):
    """Student course registration interface"""
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Check if course registration is allowed
    if not settings.allow_course_registration:
        messages.warning(request, 'Course registration is currently closed.')
        return redirect('accounts:dashboard')

    current_session = settings.current_session
    current_semester = settings.current_semester

    if not current_session or not current_semester:
        messages.error(request, 'No active session/semester. Please contact administration.')
        return redirect('accounts:dashboard')

    # Check if within registration period
    if current_semester.registration_start_date and current_semester.registration_end_date:
        today = timezone.now().date()
        if today < current_semester.registration_start_date or today > current_semester.registration_end_date:
            messages.warning(request, 'Course registration period has not started or has ended.')
            return redirect('accounts:dashboard')

    # Get available courses for student's level and department
    available_courses = Course.objects.filter(
        level=student.current_level,
        department=student.department
    ).prefetch_related('prerequisites')

    # Filter by current semester
    if current_semester.name == 'first':
        available_courses = available_courses.filter(
            Q(semester_offered='first') | Q(semester_offered='both')
        )
    else:
        available_courses = available_courses.filter(
            Q(semester_offered='second') | Q(semester_offered='both')
        )

    # Get already registered courses
    registered_course_ids = CourseRegistration.objects.filter(
        student=student,
        session=current_session,
        semester=current_semester
    ).values_list('course_id', flat=True)

    if request.method == 'POST':
        selected_course_ids = request.POST.getlist('courses')

        if not selected_course_ids:
            messages.error(request, 'Please select at least one course.')
        else:
            # Validate and register courses
            registered_count = 0

            for course_id in selected_course_ids:
                try:
                    course = Course.objects.get(id=course_id)

                    # Check if already registered
                    if course.id in registered_course_ids:
                        continue

                    # Create registration
                    CourseRegistration.objects.create(
                        student=student,
                        course=course,
                        session=current_session,
                        semester=current_semester,
                        status='pending'
                    )
                    registered_count += 1
                except Course.DoesNotExist:
                    continue

            if registered_count > 0:
                messages.success(request, f'{registered_count} course(s) registered successfully! Awaiting approval.')

            return redirect('courses:student_registered_courses')

    context = {
        'title': 'Register Courses',
        'student': student,
        'available_courses': available_courses,
        'registered_course_ids': registered_course_ids,
        'current_session': current_session,
        'current_semester': current_semester,
    }
    return render(request, 'courses/student_registration.html', context)


@login_required
@student_required
def student_registered_courses_view(request):
    """View student's registered courses"""
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Get filter parameters
    session_id = request.GET.get('session')
    semester_id = request.GET.get('semester')

    # Default to current session/semester
    if not session_id:
        session_id = settings.current_session.id if settings.current_session else None
    if not semester_id:
        semester_id = settings.current_semester.id if settings.current_semester else None

    # Get registered courses
    registrations = CourseRegistration.objects.filter(
        student=student
    ).select_related('course', 'session', 'semester')

    if session_id:
        registrations = registrations.filter(session_id=session_id)
    if semester_id:
        registrations = registrations.filter(semester_id=semester_id)

    registrations = registrations.order_by('-registration_date')

    # Calculate total credit units
    approved_registrations = registrations.filter(status='approved')
    total_units = sum(reg.course.credit_units for reg in approved_registrations)

    sessions = Session.objects.all()
    semesters = Semester.objects.all()

    context = {
        'title': 'My Registered Courses',
        'registrations': registrations,
        'total_units': total_units,
        'sessions': sessions,
        'semesters': semesters,
        'selected_session': session_id,
        'selected_semester': semester_id,
    }
    return render(request, 'courses/student_registered_courses.html', context)


# ========================== LECTURER VIEWS ==========================

@login_required
@staff_required
def lecturer_allocated_courses_view(request):
    """View lecturer's allocated courses"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    # Get filter parameters
    session_id = request.GET.get('session')
    semester_id = request.GET.get('semester')

    # Default to current session/semester
    if not session_id:
        session_id = settings.current_session.id if settings.current_session else None
    if not semester_id:
        semester_id = settings.current_semester.id if settings.current_semester else None

    # Get allocated courses
    allocations = CourseAllocation.objects.filter(
        lecturer=staff
    ).select_related('course', 'session', 'semester')

    if session_id:
        allocations = allocations.filter(session_id=session_id)
    if semester_id:
        allocations = allocations.filter(semester_id=semester_id)

    allocations = allocations.order_by('-session', '-semester')

    # Get enrolled student count for each allocation
    for allocation in allocations:
        allocation.enrolled_count = CourseRegistration.objects.filter(
            course=allocation.course,
            session=allocation.session,
            semester=allocation.semester,
            status='approved'
        ).count()

    sessions = Session.objects.all()
    semesters = Semester.objects.all()

    context = {
        'title': 'My Allocated Courses',
        'allocations': allocations,
        'sessions': sessions,
        'semesters': semesters,
        'selected_session': session_id,
        'selected_semester': semester_id,
    }
    return render(request, 'courses/lecturer_allocated_courses.html', context)


# ========================== AJAX VIEWS ==========================

@require_http_methods(["GET"])
def get_courses_by_level_ajax(request):
    """Get courses for a specific level"""
    level_id = request.GET.get('level_id')
    semester = request.GET.get('semester', '')

    if not level_id:
        return JsonResponse({'courses': []})

    courses = Course.objects.filter(level_id=level_id)

    if semester:
        courses = courses.filter(
            Q(semester_offered=semester) | Q(semester_offered='both')
        )

    courses = courses.values('id', 'code', 'title', 'credit_units', 'is_elective')

    return JsonResponse({
        'courses': list(courses)
    })


@require_http_methods(["GET"])
def get_course_prerequisites_ajax(request):
    """Get prerequisites for a course"""
    course_id = request.GET.get('course_id')

    if not course_id:
        return JsonResponse({'prerequisites': []})

    try:
        course = Course.objects.get(id=course_id)
        prerequisites = course.prerequisites.values('id', 'code', 'title')

        return JsonResponse({
            'prerequisites': list(prerequisites)
        })
    except Course.DoesNotExist:
        return JsonResponse({'prerequisites': []})


@login_required
@admin_required
@require_http_methods(["GET"])
def check_course_code_ajax(request):
    """Check if course code exists"""
    code = request.GET.get('code', '')
    course_id = request.GET.get('course_id', '')

    query = Course.objects.filter(code=code)
    if course_id:
        query = query.exclude(id=course_id)

    exists = query.exists()

    return JsonResponse({'exists': exists})


@require_http_methods(["GET"])
def get_lecturers_by_department_ajax(request):
    """Get lecturers for a specific department"""
    department_id = request.GET.get('department_id')

    if not department_id:
        return JsonResponse({'lecturers': []})

    lecturers = Staff.objects.filter(
        department_id=department_id
    ).select_related('user').values('id', 'staff_id', 'user__first_name', 'user__last_name')

    lecturers_list = [{
        'id': lec['id'],
        'staff_id': lec['staff_id'],
        'name': f"{lec['user__first_name']} {lec['user__last_name']}"
    } for lec in lecturers]

    return JsonResponse({
        'lecturers': lecturers_list
    })


@login_required
@admin_required
@require_http_methods(["POST"])
def approve_registration_ajax(request):
    """Approve single registration via AJAX"""
    try:
        registration_id = request.POST.get('registration_id')
        registration = get_object_or_404(CourseRegistration, id=registration_id)
        registration.status = 'approved'
        registration.save()

        return JsonResponse({
            'success': True,
            'message': 'Registration approved successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@admin_required
@require_http_methods(["POST"])
def reject_registration_ajax(request):
    """Reject single registration via AJAX"""
    try:
        registration_id = request.POST.get('registration_id')
        registration = get_object_or_404(CourseRegistration, id=registration_id)
        registration.status = 'rejected'
        registration.save()

        return JsonResponse({
            'success': True,
            'message': 'Registration rejected successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@admin_required
@require_http_methods(["POST"])
def bulk_approve_registrations_ajax(request):
    """Bulk approve registrations via AJAX"""
    try:
        registration_ids = request.POST.getlist('registration_ids[]')

        if not registration_ids:
            return JsonResponse({
                'success': False,
                'message': 'No registrations selected'
            }, status=400)

        count = CourseRegistration.objects.filter(
            id__in=registration_ids
        ).update(status='approved')

        return JsonResponse({
            'success': True,
            'count': count,
            'message': f'{count} registration(s) approved successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
def get_students_by_allocation(request):
    """Return students registered under a specific course allocation for the current session/semester"""
    allocation_id = request.GET.get('allocation_id')

    if not allocation_id:
        return JsonResponse({'error': 'Missing allocation_id parameter.'}, status=400)

    try:
        allocation = get_object_or_404(CourseAllocation, id=allocation_id)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)

    # Get current system session and semester
    system_settings = SystemSettings.get_instance()
    current_session = system_settings.current_session
    current_semester = system_settings.current_semester

    # If allocation has session/semester, use those instead
    session = allocation.session or current_session
    semester = allocation.semester or current_semester

    # Fetch students registered for this course in this session/semester
    registrations = CourseRegistration.objects.filter(
        course=allocation.course,
        session=session,
        semester=semester,
        status='approved'
    ).select_related('student')

    students_data = [
        {
            'id': reg.student.id,
            'matric_number': reg.student.matric_number,
            'name': f"{reg.student.user.first_name} {reg.student.user.last_name}"
        }
        for reg in registrations
    ]

    return JsonResponse({'students': students_data})
