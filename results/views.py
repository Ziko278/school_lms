from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from io import BytesIO

from .models import Result
from .forms import ResultEntryForm, ResultFilterForm
from courses.models import CourseAllocation, CourseRegistration
from admin_site.models import SystemSettings, SchoolInfo
from utils.decorators import staff_required, student_required, admin_required
from utils.helpers import calculate_gpa, calculate_cgpa


# ========================== LECTURER RESULT VIEWS ==========================

# results/views.py

@login_required
@staff_required
def result_entry_list_view(request):
    staff = request.user.staff
    settings = SystemSettings.get_instance()

    allocations = CourseAllocation.objects.filter(
        lecturer=staff,
        session=settings.current_session,
        semester=settings.current_semester
    ).select_related('course', 'session', 'semester')

    for allocation in allocations:
        students_count = CourseRegistration.objects.filter(
            course=allocation.course,
            session=allocation.session,
            semester=allocation.semester,
            status='approved'
        ).count()

        results_count = Result.objects.filter(
            course=allocation.course,
            session=allocation.session,
            semester=allocation.semester
        ).count()

        verified_count = Result.objects.filter(
            course=allocation.course,
            session=allocation.session,
            semester=allocation.semester,
            status='verified'
        ).count()

        pending_count = Result.objects.filter(
            course=allocation.course,
            session=allocation.session,
            semester=allocation.semester,
            status='pending'
        ).count()

        allocation.students_count = students_count
        allocation.results_count = results_count
        allocation.verified_count = verified_count
        allocation.pending_count = pending_count
        allocation.submission_complete = results_count >= students_count if students_count > 0 else True # Handle division by zero

        # --- Calculate Percentage Here ---
        if students_count > 0:
            allocation.entry_percentage = (results_count / students_count) * 100
        else:
            allocation.entry_percentage = 100 if results_count > 0 else 0 # Or 100 if no students? Decide logic. Let's assume 100 if results exist but no students registered.
        # --- End Calculation ---

    context = {
        'title': 'Result Entry',
        'allocations': allocations,
        'settings': settings, # Pass settings for session/semester display
    }
    return render(request, 'results/result_entry_list.html', context)


@login_required
@staff_required
def result_entry_view(request, allocation_id):
    """Enter results for all students in a course"""
    allocation = get_object_or_404(CourseAllocation, id=allocation_id)

    # Check ownership
    if allocation.lecturer != request.user.staff:
        messages.error(request, 'You do not have permission to enter results for this course.')
        return redirect('results:result_entry_list')

    # Get registered students
    registrations = CourseRegistration.objects.filter(
        course=allocation.course,
        session=allocation.session,
        semester=allocation.semester,
        status='approved'
    ).select_related('student__user').order_by('student__matric_number')

    if not registrations.exists():
        messages.warning(request, 'No students registered for this course.')
        return redirect('results:result_entry_list')

    if request.method == 'POST':
        saved_count = 0
        errors = []

        for registration in registrations:
            student = registration.student
            ca_score = request.POST.get(f'ca_score_{student.id}')
            exam_score = request.POST.get(f'exam_score_{student.id}')
            remarks = request.POST.get(f'remarks_{student.id}', '')

            if ca_score and exam_score:
                try:
                    ca_score = float(ca_score)
                    exam_score = float(exam_score)

                    # Validate scores
                    if ca_score < 0 or ca_score > 40:
                        errors.append(f"{student.matric_number}: CA score must be between 0 and 40")
                        continue

                    if exam_score < 0 or exam_score > 60:
                        errors.append(f"{student.matric_number}: Exam score must be between 0 and 60")
                        continue

                    # Create or update result
                    result, created = Result.objects.update_or_create(
                        student=student,
                        course=allocation.course,
                        session=allocation.session,
                        semester=allocation.semester,
                        defaults={
                            'ca_score': ca_score,
                            'exam_score': exam_score,
                            'remarks': remarks,
                            'submitted_by': request.user.staff,
                            'status': 'draft'  # Save as draft first
                        }
                    )
                    saved_count += 1

                except ValueError:
                    errors.append(f"{student.matric_number}: Invalid score format")

        if saved_count > 0:
            messages.success(request, f'{saved_count} result(s) saved successfully!')

        if errors:
            for error in errors[:5]:  # Show first 5 errors
                messages.error(request, error)

        return redirect('results:result_entry', allocation_id=allocation_id)

    # Get existing results
    existing_results = {}
    results = Result.objects.filter(
        course=allocation.course,
        session=allocation.session,
        semester=allocation.semester
    )
    for result in results:
        existing_results[result.student.id] = result

    context = {
        'title': f'Enter Results - {allocation.course.code}',
        'allocation': allocation,
        'registrations': registrations,
        'existing_results': existing_results,
    }
    return render(request, 'results/result_entry.html', context)


@login_required
@staff_required
def result_edit_view(request, pk):
    """Edit pending result"""
    result = get_object_or_404(Result, pk=pk)

    # Check ownership and status
    if result.submitted_by != request.user.staff:
        messages.error(request, 'You do not have permission to edit this result.')
        return redirect('results:result_entry_list')

    if result.status not in ['draft', 'rejected']:
        messages.error(request, 'Only draft or rejected results can be edited.')
        return redirect('results:result_entry_list')

    if request.method == 'POST':
        form = ResultEntryForm(request.POST, instance=result)
        if form.is_valid():
            form.save()
            messages.success(request, 'Result updated successfully!')
            return redirect('results:result_entry_list')
    else:
        form = ResultEntryForm(instance=result)

    context = {
        'title': 'Edit Result',
        'form': form,
        'result': result,
    }
    return render(request, 'results/result_form.html', context)


@login_required
@staff_required
def result_submit_view(request, allocation_id):
    """Submit results for verification"""
    if request.method == 'POST':
        allocation = get_object_or_404(CourseAllocation, id=allocation_id)

        # Check ownership
        if allocation.lecturer != request.user.staff:
            messages.error(request, 'Permission denied.')
            return redirect('results:result_entry_list')

        # Check if all results are entered
        students_count = CourseRegistration.objects.filter(
            course=allocation.course,
            session=allocation.session,
            semester=allocation.semester,
            status='approved'
        ).count()

        results_count = Result.objects.filter(
            course=allocation.course,
            session=allocation.session,
            semester=allocation.semester
        ).count()

        if results_count < students_count:
            messages.error(request, f'Please enter results for all {students_count} students before submitting.')
            return redirect('results:result_entry', allocation_id=allocation_id)

        # Mark all results as submitted (pending verification)
        updated = Result.objects.filter(
            course=allocation.course,
            session=allocation.session,
            semester=allocation.semester,
            submitted_by=request.user.staff,
            status='draft'
        ).update(
            status='pending',
            submitted_at=timezone.now()
        )

        if updated > 0:
            messages.success(request, f'{updated} result(s) submitted for verification!')
        else:
            messages.warning(request, 'No draft results found to submit.')

    return redirect('results:result_entry_list')


# ========================== RESULT VERIFICATION VIEWS ==========================

@login_required
@admin_required
def result_verification_list_view(request):
    """List pending results for verification"""
    results = Result.objects.select_related(
        'student__user', 'course', 'session', 'semester', 'submitted_by__user'
    ).all().order_by('-submitted_at')

    # Filters
    form = ResultFilterForm(request.GET)
    if form.is_valid():
        session = form.cleaned_data.get('session')
        if session:
            results = results.filter(session=session)

        semester = form.cleaned_data.get('semester')
        if semester:
            results = results.filter(semester=semester)

        department = form.cleaned_data.get('department')
        if department:
            results = results.filter(student__department=department)

        level = form.cleaned_data.get('level')
        if level:
            results = results.filter(student__current_level=level)

        status = form.cleaned_data.get('status')
        if status:
            results = results.filter(status=status)
        else:
            # Default to pending
            results = results.filter(status='pending')

    # Pagination
    paginator = Paginator(results, 50)
    page_number = request.GET.get('page')
    results_page = paginator.get_page(page_number)

    context = {
        'title': 'Result Verification',
        'results_page': results_page,
        'form': form,
    }
    return render(request, 'results/verification_list.html', context)


@login_required
@admin_required
def result_verify_view(request, pk):
    """Verify single result"""
    if request.method == 'POST':
        result = get_object_or_404(Result, pk=pk)

        result.status = 'verified'
        if hasattr(request.user, 'staff'):
            result.verified_by = request.user.staff
        result.verified_at = timezone.now()
        result.save()

        messages.success(request, f'Result verified for {result.student.matric_number}')

    return redirect('results:verification_list')


@login_required
@admin_required
def result_reject_view(request, pk):
    """Reject result"""
    if request.method == 'POST':
        result = get_object_or_404(Result, pk=pk)

        result.status = 'rejected'
        if hasattr(request.user, 'staff'):
            result.verified_by = request.user.staff
        result.verified_at = timezone.now()

        # Add rejection reason to remarks
        rejection_reason = request.POST.get('rejection_reason', '')
        if rejection_reason:
            result.remarks = f"REJECTED: {rejection_reason}\n{result.remarks}"

        result.save()

        messages.warning(request, f'Result rejected for {result.student.matric_number}')

    return redirect('results:verification_list')


# ========================== STUDENT RESULT VIEWS ==========================

@login_required
@student_required
def student_result_view(request):
    """View student's own results"""
    student = request.user.student
    settings = SystemSettings.get_instance()

    # Get filter parameters
    session_id = request.GET.get('session')
    semester_id = request.GET.get('semester')

    # Default to current session/semester
    if not session_id and settings.current_session:
        session_id = settings.current_session.id
    if not semester_id and settings.current_semester:
        semester_id = settings.current_semester.id

    # Get results
    results = Result.objects.filter(
        student=student,
        status='verified'
    ).select_related('course', 'session', 'semester')

    if session_id:
        results = results.filter(session_id=session_id)
    if semester_id:
        results = results.filter(semester_id=semester_id)

    results = results.order_by('course__code')

    # Calculate GPA for filtered results
    gpa = calculate_gpa(results) if results.exists() else 0.0

    # Calculate CGPA (all verified results)
    cgpa = calculate_cgpa(student)

    # Calculate total credit units
    total_units = sum(r.course.credit_units for r in results)

    from academics.models import Session, Semester
    sessions = Session.objects.all().order_by('-start_date')
    semesters = Semester.objects.all()

    context = {
        'title': 'My Results',
        'results': results,
        'gpa': gpa,
        'cgpa': cgpa,
        'total_units': total_units,
        'sessions': sessions,
        'semesters': semesters,
        'selected_session': int(session_id) if session_id else None,
        'selected_semester': int(semester_id) if semester_id else None,
    }
    return render(request, 'results/student_result.html', context)


@login_required
@student_required
def student_transcript_view(request):
    """View full transcript"""
    student = request.user.student

    # Get all verified results grouped by session and semester
    from academics.models import Session, Semester
    sessions = Session.objects.filter(
        results__student=student,
        results__status='verified'
    ).distinct().order_by('start_date')

    transcript_data = []
    cumulative_points = 0
    cumulative_units = 0

    for session in sessions:
        semesters = Semester.objects.filter(
            session=session,
            results__student=student,
            results__status='verified'
        ).distinct().order_by('name')

        for semester in semesters:
            results = Result.objects.filter(
                student=student,
                session=session,
                semester=semester,
                status='verified'
            ).select_related('course').order_by('course__code')

            # Calculate semester GPA
            semester_gpa = calculate_gpa(results)
            semester_units = sum(r.course.credit_units for r in results)

            # Update cumulative
            for result in results:
                cumulative_points += result.grade_point * result.course.credit_units
                cumulative_units += result.course.credit_units

            cgpa = cumulative_points / cumulative_units if cumulative_units > 0 else 0

            transcript_data.append({
                'session': session,
                'semester': semester,
                'results': results,
                'gpa': semester_gpa,
                'units': semester_units,
                'cgpa': round(cgpa, 2)
            })

    final_cgpa = calculate_cgpa(student)

    context = {
        'title': 'Academic Transcript',
        'student': student,
        'transcript_data': transcript_data,
        'final_cgpa': final_cgpa,
        'total_units': cumulative_units,
    }
    return render(request, 'results/student_transcript.html', context)


@login_required
@student_required
def result_slip_download_view(request):
    """Download result slip PDF"""
    student = request.user.student
    school_info = SchoolInfo.get_instance()

    # Get session and semester from query params
    session_id = request.GET.get('session')
    semester_id = request.GET.get('semester')

    if not session_id or not semester_id:
        messages.error(request, 'Please select session and semester.')
        return redirect('results:student_result')

    from academics.models import Session, Semester
    session = get_object_or_404(Session, id=session_id)
    semester = get_object_or_404(Semester, id=semester_id)

    # Get results
    results = Result.objects.filter(
        student=student,
        session=session,
        semester=semester,
        status='verified'
    ).select_related('course').order_by('course__code')

    if not results.exists():
        messages.error(request, 'No verified results found for selected session/semester.')
        return redirect('results:student_result')

    # Calculate GPA
    gpa = calculate_gpa(results)
    cgpa = calculate_cgpa(student)
    total_units = sum(r.course.credit_units for r in results)

    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    title_style = styles['Title']
    title_style.alignment = TA_CENTER
    elements.append(Paragraph(school_info.school_name, title_style))
    elements.append(Paragraph("RESULT SLIP", title_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Student info
    info_data = [
        ['Name:', student.user.get_full_name()],
        ['Matric Number:', student.matric_number],
        ['Department:', student.department.name],
        ['Program:', student.program.name],
        ['Level:', student.current_level.name],
        ['Session:', session.name],
        ['Semester:', semester.get_name_display()],
    ]

    info_table = Table(info_data, colWidths=[2 * inch, 4 * inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Results table
    result_data = [['Course Code', 'Course Title', 'Units', 'CA', 'Exam', 'Total', 'Grade', 'GP']]

    for result in results:
        result_data.append([
            result.course.code,
            result.course.title[:30],
            str(result.course.credit_units),
            f"{result.ca_score:.1f}",
            f"{result.exam_score:.1f}",
            f"{result.total_score:.1f}",
            result.grade,
            f"{result.grade_point:.1f}"
        ])

    result_table = Table(result_data,
                         colWidths=[1 * inch, 2.2 * inch, 0.6 * inch, 0.6 * inch, 0.6 * inch, 0.6 * inch, 0.6 * inch,
                                    0.6 * inch])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(result_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Summary
    summary_data = [
        ['Total Units:', str(total_units)],
        ['GPA:', f"{gpa:.2f}"],
        ['CGPA:', f"{cgpa:.2f}"],
    ]

    summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f'result_slip_{student.matric_number}_{session.name.replace("/", "_")}.pdf'
    response['Content-Disposition'] = f'attachment; filename={filename}'

    return response


@login_required
@student_required
def transcript_download_view(request):
    """Download full transcript PDF"""
    student = request.user.student
    school_info = SchoolInfo.get_instance()

    # Get all verified results
    from academics.models import Session, Semester
    sessions = Session.objects.filter(
        results__student=student,
        results__status='verified'
    ).distinct().order_by('start_date')

    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    title_style = styles['Title']
    title_style.alignment = TA_CENTER
    elements.append(Paragraph(school_info.school_name, title_style))
    elements.append(Paragraph("ACADEMIC TRANSCRIPT", title_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Student info
    info_data = [
        ['Name:', student.user.get_full_name()],
        ['Matric Number:', student.matric_number],
        ['Department:', student.department.name],
        ['Program:', student.program.name],
    ]

    info_table = Table(info_data, colWidths=[2 * inch, 4 * inch])
    elements.append(info_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Results by session/semester
    cumulative_units = 0

    for session in sessions:
        semesters = Semester.objects.filter(
            session=session,
            results__student=student,
            results__status='verified'
        ).distinct().order_by('name')

        for semester in semesters:
            elements.append(Paragraph(f"{session.name} - {semester.get_name_display()}", styles['Heading3']))

            results = Result.objects.filter(
                student=student,
                session=session,
                semester=semester,
                status='verified'
            ).select_related('course').order_by('course__code')

            result_data = [['Code', 'Title', 'Units', 'Grade', 'GP']]

            for result in results:
                result_data.append([
                    result.course.code,
                    result.course.title[:35],
                    str(result.course.credit_units),
                    result.grade,
                    f"{result.grade_point:.1f}"
                ])

            result_table = Table(result_data)
            result_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ]))
            elements.append(result_table)

            gpa = calculate_gpa(results)
            elements.append(Paragraph(f"Semester GPA: {gpa:.2f}", styles['Normal']))
            elements.append(Spacer(1, 0.2 * inch))

            cumulative_units += sum(r.course.credit_units for r in results)

    # Final summary
    cgpa = calculate_cgpa(student)
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(f"<b>Cumulative GPA: {cgpa:.2f}</b>", styles['Heading2']))
    elements.append(Paragraph(f"<b>Total Credit Units: {cumulative_units}</b>", styles['Heading3']))

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=transcript_{student.matric_number}.pdf'

    return response


# ========================== AJAX VIEWS ==========================

@login_required
@staff_required
@require_http_methods(["POST"])
def save_result_ajax(request):
    """Save single result via AJAX (auto-save)"""
    try:
        student_id = request.POST.get('student_id')
        course_id = request.POST.get('course_id')
        session_id = request.POST.get('session_id')
        semester_id = request.POST.get('semester_id')
        ca_score = request.POST.get('ca_score')
        exam_score = request.POST.get('exam_score')
        remarks = request.POST.get('remarks', '')

        # Validate scores
        ca_score = float(ca_score)
        exam_score = float(exam_score)

        if ca_score < 0 or ca_score > 40:
            return JsonResponse({
                'success': False,
                'message': 'CA score must be between 0 and 40'
            }, status=400)

        if exam_score < 0 or exam_score > 60:
            return JsonResponse({
                'success': False,
                'message': 'Exam score must be between 0 and 60'
            }, status=400)

        # Save result
        from accounts.models import Student
        from courses.models import Course
        from academics.models import Session, Semester

        result, created = Result.objects.update_or_create(
            student_id=student_id,
            course_id=course_id,
            session_id=session_id,
            semester_id=semester_id,
            defaults={
                'ca_score': ca_score,
                'exam_score': exam_score,
                'remarks': remarks,
                'submitted_by': request.user.staff,
                'status': 'draft'
            }
        )

        return JsonResponse({
            'success': True,
            'message': 'Result saved successfully',
            'total_score': float(result.total_score),
            'grade': result.grade,
            'grade_point': float(result.grade_point)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@admin_required
@require_http_methods(["POST"])
def verify_result_ajax(request):
    """Verify single result via AJAX"""
    try:
        result_id = request.POST.get('result_id')
        result = get_object_or_404(Result, id=result_id)

        result.status = 'verified'
        if hasattr(request.user, 'staff'):
            result.verified_by = request.user.staff
        result.verified_at = timezone.now()
        result.save()

        return JsonResponse({
            'success': True,
            'message': 'Result verified successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@admin_required
@require_http_methods(["POST"])
def bulk_verify_results_ajax(request):
    """Bulk verify results via AJAX"""
    try:
        result_ids = request.POST.getlist('result_ids[]')

        if not result_ids:
            return JsonResponse({
                'success': False,
                'message': 'No results selected'
            }, status=400)

        staff = request.user.staff if hasattr(request.user, 'staff') else None

        count = Result.objects.filter(
            id__in=result_ids
        ).update(
            status='verified',
            verified_by=staff,
            verified_at=timezone.now()
        )

        return JsonResponse({
            'success': True,
            'count': count,
            'message': f'{count} result(s) verified successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_result_stats_ajax(request):
    """Get result statistics via AJAX"""
    try:
        course_id = request.GET.get('course_id')
        session_id = request.GET.get('session_id')
        semester_id = request.GET.get('semester_id')

        results = Result.objects.filter(
            course_id=course_id,
            session_id=session_id,
            semester_id=semester_id,
            status='verified'
        )

        total = results.count()
        pass_count = results.filter(total_score__gte=40).count()
        fail_count = results.filter(total_score__lt=40).count()
        pass_rate = (pass_count / total * 100) if total > 0 else 0

        avg_score = results.aggregate(avg=Avg('total_score'))['avg'] or 0

        # Grade distribution
        grade_dist = results.values('grade').annotate(count=Count('id'))

        return JsonResponse({
            'success': True,
            'pass_rate': round(pass_rate, 2),
            'average': round(avg_score, 2),
            'grade_distribution': list(grade_dist)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@student_required
@require_http_methods(["GET"])
def calculate_gpa_ajax(request):
    """Calculate GPA for student via AJAX"""
    try:
        student = request.user.student
        session_id = request.GET.get('session_id')
        semester_id = request.GET.get('semester_id')

        results = Result.objects.filter(
            student=student,
            status='verified'
        )

        if session_id:
            results = results.filter(session_id=session_id)
        if semester_id:
            results = results.filter(semester_id=semester_id)

        gpa = calculate_gpa(results)
        cgpa = calculate_cgpa(student)

        return JsonResponse({
            'success': True,
            'gpa': round(gpa, 2),
            'cgpa': round(cgpa, 2)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@student_required
@require_http_methods(["GET"])
def get_student_results_ajax(request):
    """Get student results via AJAX"""
    try:
        student = request.user.student
        session_id = request.GET.get('session_id')
        semester_id = request.GET.get('semester_id')

        results = Result.objects.filter(
            student=student,
            status='verified'
        ).select_related('course')

        if session_id:
            results = results.filter(session_id=session_id)
        if semester_id:
            results = results.filter(semester_id=semester_id)

        results_data = [{
            'course_code': r.course.code,
            'course_title': r.course.title,
            'ca_score': float(r.ca_score),
            'exam_score': float(r.exam_score),
            'total_score': float(r.total_score),
            'grade': r.grade,
            'grade_point': float(r.grade_point)
        } for r in results]

        gpa = calculate_gpa(results)
        cgpa = calculate_cgpa(student)

        return JsonResponse({
            'success': True,
            'results': results_data,
            'gpa': round(gpa, 2),
            'cgpa': round(cgpa, 2)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)