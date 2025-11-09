from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone

from .models import ClassMaterial, Assignment, AssignmentSubmission
from .forms import (
    ClassMaterialForm, AssignmentForm, AssignmentSubmissionForm,
    AssignmentGradingForm, BulkMaterialDeleteForm
)
from courses.models import CourseAllocation, CourseRegistration
from admin_site.models import SystemSettings
from utils.decorators import staff_required, student_required


# ========================== LECTURER MATERIAL VIEWS ==========================

@login_required
@staff_required
def material_list_view(request):
    """List all materials uploaded by lecturer"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    # Get all allocations for this lecturer
    allocations = CourseAllocation.objects.filter(lecturer=staff)

    # Filter by course
    course_id = request.GET.get('course')
    if course_id:
        allocations = allocations.filter(course_id=course_id)

    # Get materials
    materials = ClassMaterial.objects.filter(
        course_allocation__in=allocations
    ).select_related('course_allocation__course').order_by('-uploaded_at')

    # Get lecturer's courses for filter
    lecturer_courses = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    # Pagination
    paginator = Paginator(materials, 20)
    page_number = request.GET.get('page')
    materials_page = paginator.get_page(page_number)

    context = {
        'title': 'Course Materials',
        'materials_page': materials_page,
        'lecturer_courses': lecturer_courses,
        'selected_course': course_id,
    }
    return render(request, 'materials/material_list.html', context)


@login_required
@staff_required
def material_upload_view(request):
    """Upload course material"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    # Get lecturer's current allocations
    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')


    if not allocations.exists():
        messages.warning(request, 'You have no course allocations for the current session/semester.')
        return redirect('materials:material_list')

    if request.method == 'POST':
        return HttpResponse(allocations)
        form = ClassMaterialForm(request.POST, request.FILES)

        if form.is_valid():
            material = form.save(commit=False)

            # Get course allocation from POST
            allocation_id = request.POST.get('course_allocation')
            try:
                allocation = CourseAllocation.objects.get(
                    id=allocation_id,
                    lecturer=staff
                )
                material.course_allocation = allocation
                material.save()

                messages.success(request, f'Material "{material.title}" uploaded successfully!')
                return redirect('materials:material_list')
            except CourseAllocation.DoesNotExist:
                messages.error(request, 'Invalid course allocation.')
    else:
        form = ClassMaterialForm()

    context = {
        'title': 'Upload Material',
        'form': form,
        'allocations': allocations,
    }
    return render(request, 'materials/material_upload.html', context)


@login_required
@staff_required
def material_edit_view(request, pk):
    """Edit material"""
    material = get_object_or_404(ClassMaterial, pk=pk)

    # Check ownership
    if material.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'You do not have permission to edit this material.')
        return redirect('materials:material_list')

    if request.method == 'POST':
        form = ClassMaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, 'Material updated successfully!')
            return redirect('materials:material_list')
    else:
        form = ClassMaterialForm(instance=material)

    context = {
        'title': 'Edit Material',
        'form': form,
        'material': material,
    }
    return render(request, 'materials/material_form.html', context)


@login_required
@staff_required
def material_delete_view(request, pk):
    """Delete material"""
    material = get_object_or_404(ClassMaterial, pk=pk)

    # Check ownership
    if material.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'You do not have permission to delete this material.')
        return redirect('materials:material_list')

    if request.method == 'POST':
        material_title = material.title
        material.delete()
        messages.success(request, f'Material "{material_title}" deleted successfully!')
        return redirect('materials:material_list')

    context = {
        'title': 'Delete Material',
        'material': material,
    }
    return render(request, 'materials/material_confirm_delete.html', context)


# ========================== STUDENT MATERIAL VIEWS ==========================

@login_required
@student_required
def student_material_list_view(request):
    """View all materials for registered courses"""
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Get registered courses
    registrations = CourseRegistration.objects.filter(
        student=student,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).select_related('course')

    registered_course_ids = [reg.course.id for reg in registrations]

    # Get materials for these courses
    materials = ClassMaterial.objects.filter(
        course_allocation__course_id__in=registered_course_ids,
        course_allocation__session=settings.current_session,
        course_allocation__semester=settings.current_semester
    ).select_related('course_allocation__course').order_by('-uploaded_at')

    # Filter by course
    course_id = request.GET.get('course')
    if course_id:
        materials = materials.filter(course_allocation__course_id=course_id)

    # Pagination
    paginator = Paginator(materials, 20)
    page_number = request.GET.get('page')
    materials_page = paginator.get_page(page_number)

    context = {
        'title': 'Course Materials',
        'materials_page': materials_page,
        'registrations': registrations,
        'selected_course': course_id,
    }
    return render(request, 'materials/student_material_list.html', context)


@login_required
@student_required
def student_material_download_view(request, pk):
    """Download/view material"""
    material = get_object_or_404(ClassMaterial, pk=pk)
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Check if student is registered for this course
    is_registered = CourseRegistration.objects.filter(
        student=student,
        course=material.course_allocation.course,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).exists()

    if not is_registered:
        messages.error(request, 'You are not registered for this course.')
        return redirect('materials:student_material_list')

    # Handle external links
    if material.material_type == 'link' and material.external_link:
        return redirect(material.external_link)

    # Handle file downloads
    if material.file:
        try:
            return FileResponse(material.file.open('rb'), as_attachment=True, filename=material.file.name)
        except Exception as e:
            messages.error(request, 'File not found.')
            return redirect('materials:student_material_list')

    messages.error(request, 'Material file not available.')
    return redirect('materials:student_material_list')


# ========================== ASSIGNMENT VIEWS (LECTURER) ==========================

@login_required
@staff_required
def assignment_list_view(request):
    """List all assignments created by lecturer"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    allocations = CourseAllocation.objects.filter(lecturer=staff)

    assignments = Assignment.objects.filter(
        course_allocation__in=allocations
    ).select_related('course_allocation__course').order_by('-created_at')

    # Filter by course
    course_id = request.GET.get('course')
    if course_id:
        assignments = assignments.filter(course_allocation__course_id=course_id)

    # Get submission stats for each assignment
    for assignment in assignments:
        assignment.submission_count = assignment.submissions.count()
        assignment.graded_count = assignment.submissions.filter(score__isnull=False).count()

    lecturer_courses = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    # Pagination
    paginator = Paginator(assignments, 20)
    page_number = request.GET.get('page')
    assignments_page = paginator.get_page(page_number)

    context = {
        'title': 'Assignments',
        'assignments_page': assignments_page,
        'lecturer_courses': lecturer_courses,
        'selected_course': course_id,
    }
    return render(request, 'materials/assignment_list.html', context)


@login_required
@staff_required
def assignment_create_view(request):
    """Create new assignment"""
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course')

    if not allocations.exists():
        messages.warning(request, 'You have no course allocations.')
        return redirect('materials:assignment_list')

    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            assignment = form.save(commit=False)

            allocation_id = request.POST.get('course_allocation')
            try:
                allocation = CourseAllocation.objects.get(
                    id=allocation_id,
                    lecturer=staff
                )
                assignment.course_allocation = allocation
                assignment.save()

                messages.success(request, f'Assignment "{assignment.title}" created successfully!')
                return redirect('materials:assignment_list')
            except CourseAllocation.DoesNotExist:
                messages.error(request, 'Invalid course allocation.')
    else:
        form = AssignmentForm()

    context = {
        'title': 'Create Assignment',
        'form': form,
        'allocations': allocations,
    }
    return render(request, 'materials/assignment_form.html', context)


@login_required
@staff_required
def assignment_edit_view(request, pk):
    """Edit assignment"""
    assignment = get_object_or_404(Assignment, pk=pk)

    if assignment.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'You do not have permission to edit this assignment.')
        return redirect('materials:assignment_list')

    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Assignment updated successfully!')
            return redirect('materials:assignment_list')
    else:
        form = AssignmentForm(instance=assignment)

    context = {
        'title': 'Edit Assignment',
        'form': form,
        'assignment': assignment,
    }
    return render(request, 'materials/assignment_form.html', context)


@login_required
@staff_required
def assignment_delete_view(request, pk):
    """Delete assignment"""
    assignment = get_object_or_404(Assignment, pk=pk)

    if assignment.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'You do not have permission to delete this assignment.')
        return redirect('materials:assignment_list')

    if request.method == 'POST':
        assignment_title = assignment.title
        assignment.delete()
        messages.success(request, f'Assignment "{assignment_title}" deleted successfully!')
        return redirect('materials:assignment_list')

    context = {
        'title': 'Delete Assignment',
        'assignment': assignment,
    }
    return render(request, 'materials/assignment_confirm_delete.html', context)


@login_required
@staff_required
def assignment_submissions_view(request, pk):
    """View all submissions for an assignment"""
    assignment = get_object_or_404(Assignment, pk=pk)

    if assignment.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'You do not have permission to view these submissions.')
        return redirect('materials:assignment_list')

    submissions = assignment.submissions.select_related('student__user').order_by('-submitted_at')

    # Statistics
    total_students = CourseRegistration.objects.filter(
        course=assignment.course_allocation.course,
        session=assignment.course_allocation.session,
        semester=assignment.course_allocation.semester,
        status='approved'
    ).count()

    submitted_count = submissions.count()
    graded_count = submissions.filter(score__isnull=False).count()
    pending_count = submissions.filter(score__isnull=True).count()

    context = {
        'title': f'Submissions - {assignment.title}',
        'assignment': assignment,
        'submissions': submissions,
        'total_students': total_students,
        'submitted_count': submitted_count,
        'graded_count': graded_count,
        'pending_count': pending_count,
    }
    return render(request, 'materials/assignment_submissions.html', context)


@login_required
@staff_required
def assignment_grading_view(request, pk):
    """Grade assignment submission"""
    submission = get_object_or_404(AssignmentSubmission, pk=pk)

    if submission.assignment.course_allocation.lecturer != request.user.staff:
        messages.error(request, 'You do not have permission to grade this submission.')
        return redirect('materials:assignment_list')

    if request.method == 'POST':
        form = AssignmentGradingForm(request.POST, instance=submission)
        if form.is_valid():
            graded_submission = form.save(commit=False)
            graded_submission.graded_at = timezone.now()
            graded_submission.save()

            messages.success(request,
                             f'Submission graded successfully! Score: {graded_submission.score}/{submission.assignment.total_marks}')
            return redirect('materials:assignment_submissions', pk=submission.assignment.id)
    else:
        form = AssignmentGradingForm(instance=submission)

    context = {
        'title': f'Grade Submission - {submission.student.matric_number}',
        'submission': submission,
        'form': form,
    }
    return render(request, 'materials/assignment_grading.html', context)


# ========================== ASSIGNMENT VIEWS (STUDENT) ==========================

@login_required
@student_required
def student_assignment_list_view(request):
    """View all assignments for registered courses"""
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Get registered courses
    registrations = CourseRegistration.objects.filter(
        student=student,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).select_related('course')

    registered_course_ids = [reg.course.id for reg in registrations]

    # Get assignments
    assignments = Assignment.objects.filter(
        course_allocation__course_id__in=registered_course_ids,
        course_allocation__session=settings.current_session,
        course_allocation__semester=settings.current_semester
    ).select_related('course_allocation__course').order_by('-due_date')

    # Add submission status to each assignment
    for assignment in assignments:
        submission = AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=student
        ).first()
        assignment.submission = submission
        assignment.is_overdue = timezone.now() > assignment.due_date

    # Filter by course
    course_id = request.GET.get('course')
    if course_id:
        assignments = assignments.filter(course_allocation__course_id=course_id)

    context = {
        'title': 'Assignments',
        'assignments': assignments,
        'registrations': registrations,
        'selected_course': course_id,
    }
    return render(request, 'materials/student_assignment_list.html', context)


@login_required
@student_required
def student_assignment_submit_view(request, pk):
    """Submit assignment"""
    assignment = get_object_or_404(Assignment, pk=pk)
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Check if registered
    is_registered = CourseRegistration.objects.filter(
        student=student,
        course=assignment.course_allocation.course,
        session=settings.current_session,
        semester=settings.current_semester,
        status='approved'
    ).exists()

    if not is_registered:
        messages.error(request, 'You are not registered for this course.')
        return redirect('materials:student_assignment_list')

    # Check if already submitted
    existing_submission = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=student
    ).first()

    if existing_submission:
        messages.warning(request, 'You have already submitted this assignment.')
        return redirect('materials:student_assignment_view_feedback', pk=existing_submission.id)

    if request.method == 'POST':
        form = AssignmentSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = student
            submission.save()

            messages.success(request, 'Assignment submitted successfully!')
            return redirect('materials:student_assignment_list')
    else:
        form = AssignmentSubmissionForm()

    context = {
        'title': f'Submit Assignment - {assignment.title}',
        'assignment': assignment,
        'form': form,
    }
    return render(request, 'materials/student_assignment_submit.html', context)


@login_required
@student_required
def student_assignment_view_feedback_view(request, pk):
    """View graded assignment feedback"""
    submission = get_object_or_404(AssignmentSubmission, pk=pk)

    if submission.student != request.user.student:
        messages.error(request, 'You do not have permission to view this submission.')
        return redirect('materials:student_assignment_list')

    context = {
        'title': 'Assignment Feedback',
        'submission': submission,
    }
    return render(request, 'materials/student_assignment_feedback.html', context)


# ========================== AJAX VIEWS ==========================

@login_required
@staff_required
@require_http_methods(["POST"])
def upload_material_ajax(request):
    """Upload material via AJAX"""
    try:
        form = ClassMaterialForm(request.POST, request.FILES)
        print(request.POST)
        if form.is_valid():
            material = form.save(commit=False)
            allocation_id = request.POST.get('course_allocation')

            allocation = get_object_or_404(
                CourseAllocation,
                id=allocation_id,
                lecturer=request.user.staff
            )

            material.course_allocation = allocation
            material.save()

            return JsonResponse({
                'success': True,
                'material_id': material.id,
                'message': 'Material uploaded successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@staff_required
@require_http_methods(["POST"])
def delete_material_ajax(request):
    """Delete material via AJAX"""
    try:
        material_id = request.POST.get('material_id')
        material = get_object_or_404(ClassMaterial, id=material_id)

        if material.course_allocation.lecturer != request.user.staff:
            return JsonResponse({
                'success': False,
                'message': 'Permission denied'
            }, status=403)

        material.delete()

        return JsonResponse({
            'success': True,
            'message': 'Material deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_materials_by_course_ajax(request):
    """Get materials for a specific course"""
    course_id = request.GET.get('course_id')

    if not course_id:
        return JsonResponse({'materials': []})

    settings = SystemSettings.get_instance()

    materials = ClassMaterial.objects.filter(
        course_allocation__course_id=course_id,
        course_allocation__session=settings.current_session,
        course_allocation__semester=settings.current_semester
    ).values('id', 'title', 'material_type', 'uploaded_at')

    return JsonResponse({
        'materials': list(materials)
    })


@login_required
@staff_required
@require_http_methods(["POST"])
def grade_assignment_ajax(request):
    """Grade assignment via AJAX"""
    try:
        submission_id = request.POST.get('submission_id')
        score = request.POST.get('score')
        feedback = request.POST.get('feedback', '')

        submission = get_object_or_404(AssignmentSubmission, id=submission_id)

        if submission.assignment.course_allocation.lecturer != request.user.staff:
            return JsonResponse({
                'success': False,
                'message': 'Permission denied'
            }, status=403)

        submission.score = float(score)
        submission.feedback = feedback
        submission.graded_at = timezone.now()
        submission.save()

        return JsonResponse({
            'success': True,
            'grade': float(score),
            'message': 'Assignment graded successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@student_required
@require_http_methods(["GET"])
def check_assignment_submission_ajax(request):
    """Check if student has submitted assignment"""
    assignment_id = request.GET.get('assignment_id')

    if not assignment_id:
        return JsonResponse({'submitted': False})

    submitted = AssignmentSubmission.objects.filter(
        assignment_id=assignment_id,
        student=request.user.student
    ).exists()

    return JsonResponse({'submitted': submitted})