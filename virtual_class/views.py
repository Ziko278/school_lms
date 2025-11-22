from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone

from .models import LiveSession, SessionParticipant, ClassRecording, Whiteboard
from .forms import LiveSessionForm, ClassRecordingForm, WhiteboardForm, WhiteboardLoadForm
from .agora_utils import get_agora_credentials
from courses.models import CourseAllocation, CourseRegistration
from admin_site.models import SystemSettings
from utils.decorators import staff_required, student_required


# ========================== LIVE SESSION VIEWS (LECTURER) ==========================

@login_required
@staff_required
@require_http_methods(["POST"])
def delete_recording_ajax(request):
    """Delete recording via AJAX"""
    try:
        recording_id = request.POST.get('recording_id')
        recording = get_object_or_404(ClassRecording, id=recording_id)

        if recording.course_allocation.lecturer != request.user.staff:
            return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

        if recording.recording_file:
            recording.recording_file.delete()

        recording.delete()

        return JsonResponse({'success': True, 'message': 'Recording deleted'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@staff_required
@require_http_methods(["GET"])
def get_recording_stats_ajax(request):
    """Get recording statistics"""
    try:
        staff = request.user.staff
        settings = SystemSettings.get_instance()

        allocations = CourseAllocation.objects.filter(
            lecturer=staff,
            session=settings.current_session,
            semester=settings.current_semester
        )

        recordings = ClassRecording.objects.filter(course_allocation__in=allocations)

        total_recordings = recordings.count()
        total_duration = "Varies"

        by_course = recordings.values(
            'course_allocation__course__code',
            'course_allocation__course__title'
        ).annotate(count=Count('id'))

        return JsonResponse({
            'success': True,
            'total_recordings': total_recordings,
            'total_duration': total_duration,
            'by_course': list(by_course)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@staff_required
def live_session_list_view(request):
    """List all live sessions for lecturer"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    # Get current allocations
    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    # Get sessions
    sessions = LiveSession.objects.filter(
        course_allocation__in=allocations
    ).select_related('course_allocation__course').order_by('-scheduled_start')

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        sessions = sessions.filter(status=status_filter)

    # Filter by course
    course_id = request.GET.get('course')
    if course_id:
        sessions = sessions.filter(course_allocation__course_id=course_id)

    # Pagination
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    sessions_page = paginator.get_page(page_number)

    context = {
        'title': 'Live Sessions',
        'sessions_page': sessions_page,
        'lecturer_courses': allocations,
        'selected_course': course_id,
        'selected_status': status_filter,
        'status_choices': LiveSession.STATUS_CHOICES,
    }
    return render(request, 'virtual_class/live_session_list.html', context)


@login_required
@staff_required
def live_session_create_view(request):
    """Create new live session"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    if not allocations.exists():
        messages.warning(request, 'You have no course allocations.')
        return redirect('virtual_class:live_session_list')

    if request.method == 'POST':
        form = LiveSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)

            # Verify ownership
            if session.course_allocation.lecturer != staff:
                messages.error(request, 'Invalid course allocation.')
                return redirect('virtual_class:live_session_list')

            session.save()
            messages.success(request, f'Live session "{session.title}" created successfully!')
            return redirect('virtual_class:live_session_list')
    else:
        form = LiveSessionForm()
        form.fields['course_allocation'].queryset = allocations

    context = {
        'title': 'Create Live Session',
        'form': form,
    }
    return render(request, 'virtual_class/live_session_form.html', context)


@login_required
@staff_required
def live_session_edit_view(request, pk):
    """Edit live session"""
    session = get_object_or_404(LiveSession, pk=pk)

    # Check ownership
    if session.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'Permission denied.')
        return redirect('virtual_class:live_session_list')

    # Can't edit live or ended sessions
    if session.status in ['live', 'ended']:
        messages.warning(request, f'Cannot edit {session.get_status_display()} session.')
        return redirect('virtual_class:live_session_list')

    if request.method == 'POST':
        form = LiveSessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, 'Session updated successfully!')
            return redirect('virtual_class:live_session_list')
    else:
        form = LiveSessionForm(instance=session)
        settings = SystemSettings.get_instance()
        form.fields['course_allocation'].queryset = CourseAllocation.objects.filter(
            lecturer=request.user.staff,
            session=settings.current_session,
            semester=settings.current_semester
        )

    context = {
        'title': 'Edit Live Session',
        'form': form,
        'session': session,
    }
    return render(request, 'virtual_class/live_session_form.html', context)


@login_required
@staff_required
def live_session_delete_view(request, pk):
    """Delete live session"""
    if request.method == 'POST':
        session = get_object_or_404(LiveSession, pk=pk)

        # Check ownership
        if session.course_allocation.lecturer != request.user.staff:
            messages.error(request, 'Permission denied.')
            return redirect('virtual_class:live_session_list')

        # Can't delete live sessions
        if session.status == 'live':
            messages.error(request, 'Cannot delete a live session. End it first.')
            return redirect('virtual_class:live_session_list')

        title = session.title
        session.delete()
        messages.success(request, f'Session "{title}" deleted successfully!')

    return redirect('virtual_class:live_session_list')


@login_required
@staff_required
def live_session_start_view(request, pk):
    """Start a live session"""
    session = get_object_or_404(LiveSession, pk=pk)

    # Check ownership
    if session.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'Permission denied.')
        return redirect('virtual_class:live_session_list')

    # Check status
    if session.status == 'live':
        messages.info(request, 'Session is already live.')
        return redirect('virtual_class:live_room', session_id=session.id)

    if session.status == 'ended':
        messages.warning(request, 'This session has already ended.')
        return redirect('virtual_class:live_session_list')

    # Start session
    session.status = 'live'
    session.actual_start = timezone.now()
    session.save()

    messages.success(request, f'Session "{session.title}" is now live!')
    return redirect('virtual_class:live_room', session_id=session.id)


@login_required
@staff_required
def live_session_end_view(request, pk):
    """End a live session"""
    if request.method == 'POST':
        session = get_object_or_404(LiveSession, pk=pk)

        # Check ownership
        if session.course_allocation.lecturer != request.user.staff:
            messages.error(request, 'Permission denied.')
            return redirect('virtual_class:live_session_list')

        if session.status != 'live':
            messages.warning(request, 'Session is not live.')
            return redirect('virtual_class:live_session_list')

        # End session
        session.status = 'ended'
        session.actual_end = timezone.now()
        session.save()

        messages.success(request, f'Session "{session.title}" has ended.')

    return redirect('virtual_class:live_session_list')


# ========================== LIVE ROOM VIEW (BOTH LECTURER & STUDENTS) ==========================

@login_required
def live_room_view(request, session_id):
    """Main live session room with video/audio and whiteboard"""
    session = get_object_or_404(LiveSession, pk=session_id)
    user = request.user

    # Determine user role
    is_lecturer = hasattr(user, 'staff') and session.course_allocation.lecturer == user.staff
    is_student = hasattr(user, 'student')

    # Check permissions
    if not is_lecturer and not is_student:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    # For students, verify registration
    if is_student:
        settings = SystemSettings.get_instance()
        is_registered = CourseRegistration.objects.filter(
            student=user.student,
            course=session.course_allocation.course,
            session=settings.current_session,
            semester=settings.current_semester,
            status='approved'
        ).exists()

        if not is_registered:
            messages.error(request, 'You are not registered for this course.')
            return redirect('virtual_class:student_live_session_list')

    # Check if session is live
    if session.status != 'live' and not is_lecturer:
        messages.warning(request, 'This session is not currently live.')
        return redirect('virtual_class:student_live_session_list')

    # Generate Agora credentials
    user_role = 'publisher' if is_lecturer else 'publisher'  # Both can publish for now
    agora_creds = get_agora_credentials(session.agora_channel_name, user_role)

    # Track participant
    if is_student:
        participant, created = SessionParticipant.objects.get_or_create(
            session=session,
            user=user,
            defaults={'joined_at': timezone.now()}
        )

    context = {
        'title': f'Live: {session.title}',
        'session': session,
        'is_lecturer': is_lecturer,
        'is_student': is_student,
        'agora_app_id': agora_creds['app_id'],
        'agora_channel': agora_creds['channel'],
        'agora_token': agora_creds['token'],
        'websocket_url': f'ws://{request.get_host()}/ws/live-session/{session.id}/',
    }
    return render(request, 'virtual_class/live_room.html', context)


# ========================== STUDENT LIVE SESSION VIEWS ==========================

@login_required
@student_required
def student_live_session_list_view(request):
    """View all live sessions for student's courses"""
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Get registered courses
    registrations = CourseRegistration.objects.filter(
        student=student,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).values_list('course_id', flat=True)

    # Get sessions
    sessions = LiveSession.objects.filter(
        course_allocation__course_id__in=registrations,
        course_allocation__session=settings.current_session,
        course_allocation__semester=settings.current_semester
    ).select_related('course_allocation__course', 'course_allocation__lecturer__user').order_by('-scheduled_start')

    # Filter by status
    status_filter = request.GET.get('status', 'live')  # Default to live sessions
    if status_filter:
        sessions = sessions.filter(status=status_filter)

    # Pagination
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    sessions_page = paginator.get_page(page_number)

    context = {
        'title': 'Live Classes',
        'sessions_page': sessions_page,
        'selected_status': status_filter,
        'status_choices': LiveSession.STATUS_CHOICES,
    }
    return render(request, 'virtual_class/student_live_session_list.html', context)


@login_required
@student_required
def student_join_session_view(request, pk):
    """Join a live session"""
    session = get_object_or_404(LiveSession, pk=pk)
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Verify registration
    is_registered = CourseRegistration.objects.filter(
        student=student,
        course=session.course_allocation.course,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).exists()

    if not is_registered:
        messages.error(request, 'You are not registered for this course.')
        return redirect('virtual_class:student_live_session_list')

    # Check if live
    if session.status != 'live':
        messages.warning(request, 'This session is not currently live.')
        return redirect('virtual_class:student_live_session_list')

    return redirect('virtual_class:live_room', session_id=session.id)


# ========================== AJAX VIEWS ==========================

@login_required
@require_http_methods(["POST"])
def get_agora_token_ajax(request):
    """Generate/refresh Agora token"""
    try:
        session_id = request.POST.get('session_id')
        session = get_object_or_404(LiveSession, pk=session_id)

        # Determine role
        is_lecturer = hasattr(request.user, 'staff') and session.course_allocation.lecturer == request.user.staff
        user_role = 'publisher' if is_lecturer else 'publisher'

        creds = get_agora_credentials(session.agora_channel_name, user_role)

        return JsonResponse({
            'success': True,
            'token': creds['token']
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def save_session_whiteboard_ajax(request):
    """Save whiteboard content during/after session"""
    try:
        session_id = request.POST.get('session_id')
        content = request.POST.get('content')

        session = get_object_or_404(LiveSession, pk=session_id)

        # Verify ownership (only lecturer can save)
        if not (hasattr(request.user, 'staff') and session.course_allocation.lecturer == request.user.staff):
            return JsonResponse({
                'success': False,
                'message': 'Permission denied'
            }, status=403)

        session.whiteboard_content = content
        session.save()

        return JsonResponse({
            'success': True,
            'message': 'Whiteboard saved'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ========================== OLD RECORDING VIEWS (KEPT FOR BACKWARDS COMPATIBILITY) ==========================

@login_required
@staff_required
def recording_list_view(request):
    """List all class recordings"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    recordings = ClassRecording.objects.filter(
        course_allocation__in=allocations
    ).select_related('course_allocation__course').order_by('-date_recorded')

    course_id = request.GET.get('course')
    if course_id:
        recordings = recordings.filter(course_allocation__course_id=course_id)

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

    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    if not allocations.exists():
        messages.warning(request, 'You have no course allocations.')
        return redirect('virtual_class:recording_list')

    if request.method == 'POST':
        form = ClassRecordingForm(request.POST, request.FILES)
        if form.is_valid():
            recording = form.save(commit=False)

            allocation = recording.course_allocation
            if allocation.lecturer != staff:
                messages.error(request, 'Invalid course allocation.')
                return redirect('virtual_class:recording_list')

            recording.save()
            messages.success(request, 'Recording uploaded successfully!')
            return redirect('virtual_class:recording_list')
    else:
        form = ClassRecordingForm()
        form.fields['course_allocation'].queryset = allocations

    context = {
        'title': 'Upload Recording',
        'form': form,
    }
    return render(request, 'virtual_class/recording_form.html', context)


@login_required
@staff_required
def recording_edit_view(request, pk):
    """Edit class recording"""
    recording = get_object_or_404(ClassRecording, pk=pk)

    if recording.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'Permission denied.')
        return redirect('virtual_class:recording_list')

    if request.method == 'POST':
        form = ClassRecordingForm(request.POST, request.FILES, instance=recording)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recording updated!')
            return redirect('virtual_class:recording_list')
    else:
        form = ClassRecordingForm(instance=recording)
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

        if recording.course_allocation.lecturer != request.user.staff:
            messages.error(request, 'Permission denied.')
            return redirect('virtual_class:recording_list')

        if recording.recording_file:
            recording.recording_file.delete()

        recording.delete()
        messages.success(request, 'Recording deleted!')

    return redirect('virtual_class:recording_list')


@login_required
@student_required
def student_recording_list_view(request):
    """View recordings for student's courses"""
    student = request.user.student
    settings = SystemSettings.get_instance()

    registrations = CourseRegistration.objects.filter(
        student=student,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).values_list('course_id', flat=True)

    recordings = ClassRecording.objects.filter(
        course_allocation__course_id__in=registrations,
        course_allocation__session=settings.current_session,
        course_allocation__semester=settings.current_semester
    ).select_related('course_allocation__course').order_by('-date_recorded')

    course_id = request.GET.get('course')
    if course_id:
        recordings = recordings.filter(course_allocation__course_id=course_id)

    from courses.models import Course
    student_courses = Course.objects.filter(id__in=registrations)

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
    """View individual recording"""
    recording = get_object_or_404(ClassRecording, pk=pk)
    student = request.user.student
    settings = SystemSettings.get_instance()

    is_registered = CourseRegistration.objects.filter(
        student=student,
        course=recording.course_allocation.course,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).exists()

    if not is_registered:
        messages.error(request, 'Not registered for this course.')
        return redirect('virtual_class:student_recording_list')

    context = {
        'title': f'Recording - {recording.title}',
        'recording': recording,
    }
    return render(request, 'virtual_class/student_recording_view.html', context)


# OLD WHITEBOARD VIEWS (KEPT)
@login_required
@staff_required
def whiteboard_view(request):
    """Display whiteboard interface"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    if not allocations.exists():
        messages.warning(request, 'No course allocations.')
        return redirect('accounts:dashboard')

    whiteboard_id = request.GET.get('whiteboard_id')
    whiteboard = None

    if whiteboard_id:
        whiteboard = get_object_or_404(Whiteboard, id=whiteboard_id)
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

            allocation_id = request.POST.get('allocation_id')
            allocation = get_object_or_404(CourseAllocation, id=allocation_id)

            if allocation.lecturer != request.user.staff:
                messages.error(request, 'Permission denied.')
                return redirect('virtual_class:whiteboard')

            whiteboard.course_allocation = allocation
            whiteboard.session = allocation.session
            whiteboard.semester = allocation.semester
            whiteboard.save()

            messages.success(request, 'Whiteboard saved!')
            return redirect('virtual_class:whiteboard_list')

    return redirect('virtual_class:whiteboard')


@login_required
@staff_required
def whiteboard_list_view(request):
    """List saved whiteboards"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    )

    whiteboards = Whiteboard.objects.filter(
        course_allocation__in=allocations
    ).select_related('course_allocation__course').order_by('-updated_at')

    course_id = request.GET.get('course')
    if course_id:
        whiteboards = whiteboards.filter(course_allocation__course_id=course_id)

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
    """Load whiteboard"""
    whiteboard = get_object_or_404(Whiteboard, pk=pk)

    if whiteboard.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'Permission denied.')
        return redirect('virtual_class:whiteboard_list')

    return redirect(f'/virtual-class/whiteboard/?whiteboard_id={pk}')


@login_required
@staff_required
def whiteboard_delete_view(request, pk):
    """Delete whiteboard"""
    if request.method == 'POST':
        whiteboard = get_object_or_404(Whiteboard, pk=pk)

        if whiteboard.course_allocation.lecturer != request.user.staff:
            messages.error(request, 'Permission denied.')
            return redirect('virtual_class:whiteboard_list')

        whiteboard.delete()
        messages.success(request, 'Whiteboard deleted!')

    return redirect('virtual_class:whiteboard_list')


@login_required
@student_required
def student_whiteboard_list_view(request):
    """List whiteboards for student"""
    student = request.user.student
    settings = SystemSettings.get_instance()

    registrations = CourseRegistration.objects.filter(
        student=student,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).values_list('course_id', flat=True)

    whiteboards = Whiteboard.objects.filter(
        course_allocation__course_id__in=registrations,
        course_allocation__session=settings.current_session,
        course_allocation__semester=settings.current_semester
    ).select_related('course_allocation__course', 'course_allocation__lecturer__user').order_by('-updated_at')

    course_id = request.GET.get('course')
    if course_id:
        whiteboards = whiteboards.filter(course_allocation__course_id=course_id)

    from courses.models import Course
    student_courses = Course.objects.filter(id__in=registrations)

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


@login_required
@student_required
def student_whiteboard_view_view(request, pk):
    """View whiteboard"""
    whiteboard = get_object_or_404(Whiteboard, pk=pk)
    student = request.user.student
    settings = SystemSettings.get_instance()

    is_registered = CourseRegistration.objects.filter(
        student=student,
        course=whiteboard.course_allocation.course,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).exists()

    if not is_registered:
        messages.error(request, 'Not registered.')
        return redirect('accounts:dashboard')

    context = {
        'title': f'Whiteboard - {whiteboard.title}',
        'whiteboard': whiteboard,
        'read_only': True,
    }
    return render(request, 'virtual_class/whiteboard_view.html', context)


@login_required
@staff_required
@require_http_methods(["POST"])
def save_whiteboard_ajax(request):
    """Auto-save whiteboard"""
    try:
        allocation_id = request.POST.get('allocation_id')
        title = request.POST.get('title')
        content = request.POST.get('content')
        whiteboard_id = request.POST.get('whiteboard_id')

        allocation = get_object_or_404(CourseAllocation, id=allocation_id)

        if allocation.lecturer != request.user.staff:
            return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

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

        return JsonResponse({'success': True, 'whiteboard_id': whiteboard.id, 'message': 'Saved'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@staff_required
@require_http_methods(["GET"])
def load_whiteboard_ajax(request):
    """Load whiteboard"""
    try:
        whiteboard_id = request.GET.get('whiteboard_id')
        whiteboard = get_object_or_404(Whiteboard, id=whiteboard_id)

        if whiteboard.course_allocation.lecturer != request.user.staff:
            return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

        return JsonResponse({'success': True, 'content': whiteboard.content, 'title': whiteboard.title})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


