from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Count

from .models import ClassRecording, Whiteboard
from .forms import ClassRecordingForm, WhiteboardForm, WhiteboardLoadForm
from courses.models import CourseAllocation
from admin_site.models import SystemSettings
from utils.decorators import staff_required, student_required


# ========================== RECORDING VIEWS (LECTURER) ==========================

@login_required
@staff_required
def recording_list_view(request):
    """List all class recordings"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    # Get current allocations
    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    # Get recordings for current allocations
    recordings = ClassRecording.objects.filter(
        course_allocation__in=allocations
    ).select_related('course_allocation__course').order_by('-date_recorded')

    # Filter by course if provided
    course_id = request.GET.get('course')
    if course_id:
        recordings = recordings.filter(course_allocation__course_id=course_id)

    # Pagination
    paginator = Paginator(recordings, 20)
    page_number = request.GET.get('page')
    recordings_page = paginator.get_page(page_number)

    context = {
        'title': 'Class Recordings',
        'recordings_page': recordings_page,
        'lecturer_courses': allocations,
        'selected_course': course_id,
    }
    return render(request, 'virtual_class/recording_list.html', context)


@login_required
@staff_required
def recording_upload_view(request):
    """Upload class recording"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    # Get current allocations
    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    if not allocations.exists():
        messages.warning(request, 'You have no course allocations for the current session/semester.')
        return redirect('virtual_class:recording_list')

    if request.method == 'POST':
        form = ClassRecordingForm(request.POST, request.FILES)
        if form.is_valid():
            recording = form.save(commit=False)

            # Verify the allocation belongs to the lecturer
            allocation = recording.course_allocation
            if allocation.lecturer != staff:
                messages.error(request, 'Invalid course allocation.')
                return redirect('virtual_class:recording_list')

            recording.save()
            messages.success(request, 'Class recording uploaded successfully!')
            return redirect('virtual_class:recording_list')
    else:
        form = ClassRecordingForm()
        # Filter allocations for the form
        form.fields['course_allocation'].queryset = allocations

    context = {
        'title': 'Upload Class Recording',
        'form': form,
    }
    return render(request, 'virtual_class/recording_form.html', context)


@login_required
@staff_required
def recording_edit_view(request, pk):
    """Edit class recording"""
    recording = get_object_or_404(ClassRecording, pk=pk)

    # Check ownership
    if recording.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'You do not have permission to edit this recording.')
        return redirect('virtual_class:recording_list')

    if request.method == 'POST':
        form = ClassRecordingForm(request.POST, request.FILES, instance=recording)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recording updated successfully!')
            return redirect('virtual_class:recording_list')
    else:
        form = ClassRecordingForm(instance=recording)
        # Ensure user can only select their own allocations
        settings = SystemSettings.get_instance()
        form.fields['course_allocation'].queryset = CourseAllocation.objects.filter(
            lecturer=request.user.staff,
            session=settings.current_session,
            semester=settings.current_semester
        )

    context = {
        'title': 'Edit Recording',
        'form': form,
        'recording': recording,
    }
    return render(request, 'virtual_class/recording_form.html', context)


@login_required
@staff_required
def recording_delete_view(request, pk):
    """Delete class recording"""
    if request.method == 'POST':
        recording = get_object_or_404(ClassRecording, pk=pk)

        # Check ownership
        if recording.course_allocation.lecturer != request.user.staff:
            messages.error(request, 'You do not have permission to delete this recording.')
            return redirect('virtual_class:recording_list')

        # Delete the file if it exists
        if recording.recording_file:
            recording.recording_file.delete()

        recording.delete()
        messages.success(request, 'Recording deleted successfully!')

    return redirect('virtual_class:recording_list')


# ========================== STUDENT RECORDING VIEWS ==========================

@login_required
@student_required
def student_recording_list_view(request):
    """View all recordings for student's registered courses"""
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Get student's registered courses
    from courses.models import CourseRegistration
    registrations = CourseRegistration.objects.filter(
        student=student,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).values_list('course_id', flat=True)

    # Get recordings for those courses
    recordings = ClassRecording.objects.filter(
        course_allocation__course_id__in=registrations,
        course_allocation__session=settings.current_session,
        course_allocation__semester=settings.current_semester
    ).select_related('course_allocation__course').order_by('-date_recorded')

    # Filter by course if provided
    course_id = request.GET.get('course')
    if course_id:
        recordings = recordings.filter(course_allocation__course_id=course_id)

    # Get courses for filter dropdown
    from courses.models import Course
    student_courses = Course.objects.filter(id__in=registrations)

    # Pagination
    paginator = Paginator(recordings, 20)
    page_number = request.GET.get('page')
    recordings_page = paginator.get_page(page_number)

    context = {
        'title': 'Class Recordings',
        'recordings_page': recordings_page,
        'student_courses': student_courses,
        'selected_course': course_id,
    }
    return render(request, 'virtual_class/student_recording_list.html', context)


@login_required
@student_required
def student_recording_view_view(request, pk):
    """View/stream individual recording"""
    recording = get_object_or_404(ClassRecording, pk=pk)
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Verify student is registered for this course
    from courses.models import CourseRegistration
    is_registered = CourseRegistration.objects.filter(
        student=student,
        course=recording.course_allocation.course,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).exists()

    if not is_registered:
        messages.error(request, 'You are not registered for this course.')
        return redirect('virtual_class:student_recording_list')

    context = {
        'title': f'Recording - {recording.title}',
        'recording': recording,
    }
    return render(request, 'virtual_class/student_recording_view.html', context)


# ========================== WHITEBOARD VIEWS (LECTURER) ==========================

@login_required
@staff_required
def whiteboard_view(request):
    """Display whiteboard interface"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    # Get current allocations
    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    if not allocations.exists():
        messages.warning(request, 'You have no course allocations.')
        return redirect('accounts:dashboard')

    # Get whiteboard_id from query params if loading existing
    whiteboard_id = request.GET.get('whiteboard_id')
    whiteboard = None

    if whiteboard_id:
        whiteboard = get_object_or_404(Whiteboard, id=whiteboard_id)
        # Verify ownership
        if whiteboard.course_allocation.lecturer != staff:
            messages.error(request, 'Permission denied.')
            return redirect('virtual_class:whiteboard_list')

    context = {
        'title': 'Virtual Whiteboard',
        'allocations': allocations,
        'whiteboard': whiteboard,
    }
    return render(request, 'virtual_class/whiteboard.html', context)


@login_required
@staff_required
def whiteboard_save_view(request):
    """Save whiteboard content"""
    if request.method == 'POST':
        form = WhiteboardForm(request.POST)
        if form.is_valid():
            whiteboard = form.save(commit=False)

            # Get allocation from POST data
            allocation_id = request.POST.get('allocation_id')
            allocation = get_object_or_404(CourseAllocation, id=allocation_id)

            # Verify ownership
            if allocation.lecturer != request.user.staff:
                messages.error(request, 'Permission denied.')
                return redirect('virtual_class:whiteboard')

            whiteboard.course_allocation = allocation
            whiteboard.session = allocation.session
            whiteboard.semester = allocation.semester
            whiteboard.save()

            messages.success(request, 'Whiteboard saved successfully!')
            return redirect('virtual_class:whiteboard_list')
    else:
        form = WhiteboardForm()

    return redirect('virtual_class:whiteboard')


@login_required
@staff_required
def whiteboard_list_view(request):
    """List saved whiteboards"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    # Get whiteboards for current allocations
    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    )

    whiteboards = Whiteboard.objects.filter(
        course_allocation__in=allocations
    ).select_related('course_allocation__course').order_by('-updated_at')

    # Filter by course
    course_id = request.GET.get('course')
    if course_id:
        whiteboards = whiteboards.filter(course_allocation__course_id=course_id)

    # Pagination
    paginator = Paginator(whiteboards, 20)
    page_number = request.GET.get('page')
    whiteboards_page = paginator.get_page(page_number)

    context = {
        'title': 'Saved Whiteboards',
        'whiteboards_page': whiteboards_page,
        'lecturer_courses': allocations,
        'selected_course': course_id,
    }
    return render(request, 'virtual_class/whiteboard_list.html', context)


@login_required
@staff_required
def whiteboard_load_view(request, pk):
    """Load existing whiteboard"""
    whiteboard = get_object_or_404(Whiteboard, pk=pk)

    # Check ownership
    if whiteboard.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'Permission denied.')
        return redirect('virtual_class:whiteboard_list')

    # Redirect to whiteboard with ID
    return redirect(f'/virtual-class/whiteboard/?whiteboard_id={pk}')


@login_required
@staff_required
def whiteboard_delete_view(request, pk):
    """Delete saved whiteboard"""
    if request.method == 'POST':
        whiteboard = get_object_or_404(Whiteboard, pk=pk)

        # Check ownership
        if whiteboard.course_allocation.lecturer != request.user.staff:
            messages.error(request, 'Permission denied.')
            return redirect('virtual_class:whiteboard_list')

        whiteboard.delete()
        messages.success(request, 'Whiteboard deleted successfully!')

    return redirect('virtual_class:whiteboard_list')


# ========================== STUDENT WHITEBOARD VIEWS ==========================

@login_required
@student_required
def student_whiteboard_view_view(request, pk):
    """View saved whiteboard (read-only for students)"""
    whiteboard = get_object_or_404(Whiteboard, pk=pk)
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Verify student is registered for this course
    from courses.models import CourseRegistration
    is_registered = CourseRegistration.objects.filter(
        student=student,
        course=whiteboard.course_allocation.course,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).exists()

    if not is_registered:
        messages.error(request, 'You are not registered for this course.')
        return redirect('accounts:dashboard')

    context = {
        'title': f'Whiteboard - {whiteboard.title}',
        'whiteboard': whiteboard,
        'read_only': True,
    }
    return render(request, 'virtual_class/whiteboard_view.html', context)


# ========================== AJAX VIEWS ==========================

@login_required
@staff_required
@require_http_methods(["POST"])
def save_whiteboard_ajax(request):
    """Auto-save whiteboard content via AJAX"""
    try:
        allocation_id = request.POST.get('allocation_id')
        title = request.POST.get('title')
        content = request.POST.get('content')
        whiteboard_id = request.POST.get('whiteboard_id')

        # Get allocation
        allocation = get_object_or_404(CourseAllocation, id=allocation_id)

        # Verify ownership
        if allocation.lecturer != request.user.staff:
            return JsonResponse({
                'success': False,
                'message': 'Permission denied'
            }, status=403)

        # Update or create whiteboard
        if whiteboard_id:
            whiteboard = get_object_or_404(Whiteboard, id=whiteboard_id)
            whiteboard.title = title
            whiteboard.content = content
            whiteboard.save()
        else:
            whiteboard = Whiteboard.objects.create(
                course_allocation=allocation,
                session=allocation.session,
                semester=allocation.semester,
                title=title,
                content=content
            )

        return JsonResponse({
            'success': True,
            'whiteboard_id': whiteboard.id,
            'message': 'Whiteboard saved successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@staff_required
@require_http_methods(["GET"])
def load_whiteboard_ajax(request):
    """Load whiteboard content via AJAX"""
    try:
        whiteboard_id = request.GET.get('whiteboard_id')
        whiteboard = get_object_or_404(Whiteboard, id=whiteboard_id)

        # Verify ownership
        if whiteboard.course_allocation.lecturer != request.user.staff:
            return JsonResponse({
                'success': False,
                'message': 'Permission denied'
            }, status=403)

        return JsonResponse({
            'success': True,
            'content': whiteboard.content,
            'title': whiteboard.title
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@staff_required
@require_http_methods(["POST"])
def delete_recording_ajax(request):
    """Delete recording via AJAX"""
    try:
        recording_id = request.POST.get('recording_id')
        recording = get_object_or_404(ClassRecording, id=recording_id)

        # Verify ownership
        if recording.course_allocation.lecturer != request.user.staff:
            return JsonResponse({
                'success': False,
                'message': 'Permission denied'
            }, status=403)

        # Delete file if exists
        if recording.recording_file:
            recording.recording_file.delete()

        recording.delete()

        return JsonResponse({
            'success': True,
            'message': 'Recording deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@staff_required
@require_http_methods(["GET"])
def get_recording_stats_ajax(request):
    """Get recording statistics via AJAX"""
    try:
        staff = request.user.staff
        settings = SystemSettings.get_instance()

        allocations = CourseAllocation.objects.filter(
            lecturer=staff,
            session=settings.current_session,
            semester=settings.current_semester
        )

        recordings = ClassRecording.objects.filter(
            course_allocation__in=allocations
        )

        total_recordings = recordings.count()

        # Calculate total duration (simplified - assumes format like "1h 30m")
        total_duration = "Varies"  # You can implement proper duration calculation

        # Get recordings by course
        by_course = recordings.values(
            'course_allocation__course__code',
            'course_allocation__course__title'
        ).annotate(
            count=Count('id')
        )

        return JsonResponse({
            'success': True,
            'total_recordings': total_recordings,
            'total_duration': total_duration,
            'by_course': list(by_course)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@student_required
def student_whiteboard_list_view(request):
    """List all whiteboards for student's registered courses"""
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Get student's registered courses
    from courses.models import CourseRegistration
    registrations = CourseRegistration.objects.filter(
        student=student,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).values_list('course_id', flat=True)

    # Get whiteboards for those courses
    whiteboards = Whiteboard.objects.filter(
        course_allocation__course_id__in=registrations,
        course_allocation__session=settings.current_session,
        course_allocation__semester=settings.current_semester
    ).select_related('course_allocation__course', 'course_allocation__lecturer__user').order_by('-updated_at')

    # Filter by course if provided
    course_id = request.GET.get('course')
    if course_id:
        whiteboards = whiteboards.filter(course_allocation__course_id=course_id)

    # Get courses for filter dropdown
    from courses.models import Course
    student_courses = Course.objects.filter(id__in=registrations)

    # Pagination
    paginator = Paginator(whiteboards, 20)
    page_number = request.GET.get('page')
    whiteboards_page = paginator.get_page(page_number)

    context = {
        'title': 'Saved Whiteboards',
        'whiteboards_page': whiteboards_page,
        'student_courses': student_courses,
        'selected_course': course_id,
    }
    return render(request, 'virtual_class/student_whiteboard_list.html', context)