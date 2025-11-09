from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count

from .models import Session, Semester, Department, Program, Level
from .forms import SessionForm, SemesterForm, DepartmentForm, ProgramForm, LevelForm
from utils.decorators import admin_required


# ========================== SESSION VIEWS ==========================

@login_required
@admin_required
def session_list_view(request):
    """List all academic sessions"""
    sessions = Session.objects.all().order_by('-start_date')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        sessions = sessions.filter(name__icontains=search_query)

    # Pagination
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    sessions_page = paginator.get_page(page_number)

    context = {
        'title': 'Academic Sessions',
        'sessions_page': sessions_page,
        'search_query': search_query,
    }
    return render(request, 'academics/session_list.html', context)


@login_required
@admin_required
def session_create_view(request):
    """Create new academic session"""
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save()
            messages.success(request, f'Session {session.name} created successfully!')
            return redirect('academics:session_list')
    else:
        form = SessionForm()

    context = {
        'title': 'Create Session',
        'form': form,
    }
    return render(request, 'academics/session_form.html', context)


@login_required
@admin_required
def session_edit_view(request, pk):
    """Edit academic session"""
    session = get_object_or_404(Session, pk=pk)

    if request.method == 'POST':
        form = SessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, f'Session {session.name} updated successfully!')
            return redirect('academics:session_list')
    else:
        form = SessionForm(instance=session)

    context = {
        'title': 'Edit Session',
        'form': form,
        'session': session,
    }
    return render(request, 'academics/session_form.html', context)


@login_required
@admin_required
def session_delete_view(request, pk):
    """Delete academic session"""
    session = get_object_or_404(Session, pk=pk)

    if request.method == 'POST':
        # Check if session has dependencies
        if session.admitted_students.exists() or session.course_registrations.exists():
            messages.error(request, 'Cannot delete session with existing students or course registrations.')
            return redirect('academics:session_list')

        session_name = session.name
        session.delete()
        messages.success(request, f'Session {session_name} deleted successfully!')
        return redirect('academics:session_list')

    context = {
        'title': 'Delete Session',
        'session': session,
    }
    return render(request, 'academics/session_confirm_delete.html', context)


@login_required
@admin_required
def session_activate_view(request, pk):
    """Activate academic session"""
    if request.method == 'POST':
        session = get_object_or_404(Session, pk=pk)
        session.activate()

        # Update system settings
        from admin_site.models import SystemSettings
        settings = SystemSettings.get_instance()
        settings.current_session = session
        settings.save()

        messages.success(request, f'Session {session.name} activated successfully!')

    return redirect('academics:session_list')


# ========================== SEMESTER VIEWS ==========================

@login_required
@admin_required
def semester_list_view(request):
    """List all semesters"""
    semesters = Semester.objects.select_related('session').all().order_by('-session__start_date', 'name')

    # Filter by session
    session_id = request.GET.get('session', '')
    if session_id:
        semesters = semesters.filter(session_id=session_id)

    # Pagination
    paginator = Paginator(semesters, 20)
    page_number = request.GET.get('page')
    semesters_page = paginator.get_page(page_number)

    sessions = Session.objects.all()

    context = {
        'title': 'Semesters',
        'semesters_page': semesters_page,
        'sessions': sessions,
        'selected_session': session_id,
    }
    return render(request, 'academics/semester_list.html', context)


@login_required
@admin_required
def semester_create_view(request):
    """Create new semester"""
    if request.method == 'POST':
        form = SemesterForm(request.POST)
        if form.is_valid():
            semester = form.save()
            messages.success(request, f'Semester {semester} created successfully!')
            return redirect('academics:semester_list')
    else:
        form = SemesterForm()

    context = {
        'title': 'Create Semester',
        'form': form,
    }
    return render(request, 'academics/semester_form.html', context)


@login_required
@admin_required
def semester_edit_view(request, pk):
    """Edit semester"""
    semester = get_object_or_404(Semester, pk=pk)

    if request.method == 'POST':
        form = SemesterForm(request.POST, instance=semester)
        if form.is_valid():
            form.save()
            messages.success(request, f'Semester {semester} updated successfully!')
            return redirect('academics:semester_list')
    else:
        form = SemesterForm(instance=semester)

    context = {
        'title': 'Edit Semester',
        'form': form,
        'semester': semester,
    }
    return render(request, 'academics/semester_form.html', context)


@login_required
@admin_required
def semester_delete_view(request, pk):
    """Delete semester"""
    semester = get_object_or_404(Semester, pk=pk)

    if request.method == 'POST':
        # Check if semester has dependencies
        if semester.course_registrations.exists():
            messages.error(request, 'Cannot delete semester with existing course registrations.')
            return redirect('academics:semester_list')

        semester_name = str(semester)
        semester.delete()
        messages.success(request, f'Semester {semester_name} deleted successfully!')
        return redirect('academics:semester_list')

    context = {
        'title': 'Delete Semester',
        'semester': semester,
    }
    return render(request, 'academics/semester_confirm_delete.html', context)


@login_required
@admin_required
def semester_activate_view(request, pk):
    """Activate semester"""
    if request.method == 'POST':
        semester = get_object_or_404(Semester, pk=pk)
        semester.activate()

        # Update system settings
        from admin_site.models import SystemSettings
        settings = SystemSettings.get_instance()
        settings.current_semester = semester
        settings.save()

        messages.success(request, f'Semester {semester} activated successfully!')

    return redirect('academics:semester_list')


# ========================== DEPARTMENT VIEWS ==========================

@login_required
@admin_required
def department_list_view(request):
    """List all departments"""
    departments = Department.objects.select_related('hod__user').annotate(
        student_count=Count('students'),
        staff_count=Count('staff_members')
    ).all()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        departments = departments.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query)
        )

    context = {
        'title': 'Departments',
        'departments': departments,
        'search_query': search_query,
    }
    return render(request, 'academics/department_list.html', context)


@login_required
@admin_required
def department_create_view(request):
    """Create new department"""
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save()
            messages.success(request, f'Department {department.name} created successfully!')
            return redirect('academics:department_list')
    else:
        form = DepartmentForm()

    context = {
        'title': 'Create Department',
        'form': form,
    }
    return render(request, 'academics/department_form.html', context)


@login_required
@admin_required
def department_edit_view(request, pk):
    """Edit department"""
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, f'Department {department.name} updated successfully!')
            return redirect('academics:department_list')
    else:
        form = DepartmentForm(instance=department)

    context = {
        'title': 'Edit Department',
        'form': form,
        'department': department,
    }
    return render(request, 'academics/department_form.html', context)


@login_required
@admin_required
def department_detail_view(request, pk):
    """View department details"""
    department = get_object_or_404(
        Department.objects.select_related('hod__user').annotate(
            student_count=Count('students'),
            staff_count=Count('staff_members')
        ),
        pk=pk
    )

    # Get programs
    programs = department.programs.annotate(
        student_count=Count('students')
    ).all()

    # Get staff members
    staff_members = department.staff_members.select_related('user')[:10]

    # Get courses
    from courses.models import Course
    courses = Course.objects.filter(department=department).count()

    context = {
        'title': f'{department.name}',
        'department': department,
        'programs': programs,
        'staff_members': staff_members,
        'total_courses': courses,
    }
    return render(request, 'academics/department_detail.html', context)


@login_required
@admin_required
def department_delete_view(request, pk):
    """Delete department"""
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        # Check if department has dependencies
        if department.students.exists() or department.staff_members.exists():
            messages.error(request, 'Cannot delete department with existing students or staff.')
            return redirect('academics:department_list')

        dept_name = department.name
        department.delete()
        messages.success(request, f'Department {dept_name} deleted successfully!')
        return redirect('academics:department_list')

    context = {
        'title': 'Delete Department',
        'department': department,
    }
    return render(request, 'academics/department_confirm_delete.html', context)


# ========================== PROGRAM VIEWS ==========================

@login_required
@admin_required
def program_list_view(request):
    """List all programs"""
    programs = Program.objects.select_related('department').annotate(
        student_count=Count('students')
    ).all()

    # Filter by department
    department_id = request.GET.get('department', '')
    if department_id:
        programs = programs.filter(department_id=department_id)

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        programs = programs.filter(name__icontains=search_query)

    departments = Department.objects.all()

    context = {
        'title': 'Programs',
        'programs': programs,
        'departments': departments,
        'selected_department': department_id,
        'search_query': search_query,
    }
    return render(request, 'academics/program_list.html', context)


@login_required
@admin_required
def program_create_view(request):
    """Create new program"""
    if request.method == 'POST':
        form = ProgramForm(request.POST)
        if form.is_valid():
            program = form.save()
            messages.success(request, f'Program {program.name} created successfully!')
            return redirect('academics:program_list')
    else:
        form = ProgramForm()

    context = {
        'title': 'Create Program',
        'form': form,
    }
    return render(request, 'academics/program_form.html', context)


@login_required
@admin_required
def program_edit_view(request, pk):
    """Edit program"""
    program = get_object_or_404(Program, pk=pk)

    if request.method == 'POST':
        form = ProgramForm(request.POST, instance=program)
        if form.is_valid():
            form.save()
            messages.success(request, f'Program {program.name} updated successfully!')
            return redirect('academics:program_list')
    else:
        form = ProgramForm(instance=program)

    context = {
        'title': 'Edit Program',
        'form': form,
        'program': program,
    }
    return render(request, 'academics/program_form.html', context)


@login_required
@admin_required
def program_detail_view(request, pk):
    """View program details"""
    program = get_object_or_404(
        Program.objects.select_related('department').annotate(
            student_count=Count('students')
        ),
        pk=pk
    )

    # Get levels
    levels = program.levels.all().order_by('order')

    # Get students
    students = program.students.select_related('user', 'current_level')[:10]

    context = {
        'title': f'{program.name}',
        'program': program,
        'levels': levels,
        'students': students,
    }
    return render(request, 'academics/program_detail.html', context)


@login_required
@admin_required
def program_delete_view(request, pk):
    """Delete program"""
    program = get_object_or_404(Program, pk=pk)

    if request.method == 'POST':
        # Check if program has dependencies
        if program.students.exists():
            messages.error(request, 'Cannot delete program with existing students.')
            return redirect('academics:program_list')

        program_name = program.name
        program.delete()
        messages.success(request, f'Program {program_name} deleted successfully!')
        return redirect('academics:program_list')

    context = {
        'title': 'Delete Program',
        'program': program,
    }
    return render(request, 'academics/program_confirm_delete.html', context)


# ========================== LEVEL VIEWS ==========================

@login_required
@admin_required
def level_list_view(request):
    """List all levels"""
    levels = Level.objects.select_related('program__department').annotate(
        student_count=Count('students')
    ).all().order_by('program', 'order')

    # Filter by program
    program_id = request.GET.get('program', '')
    if program_id:
        levels = levels.filter(program_id=program_id)

    programs = Program.objects.select_related('department').all()

    context = {
        'title': 'Levels',
        'levels': levels,
        'programs': programs,
        'selected_program': program_id,
    }
    return render(request, 'academics/level_list.html', context)


@login_required
@admin_required
def level_create_view(request):
    """Create new level"""
    if request.method == 'POST':
        form = LevelForm(request.POST)
        if form.is_valid():
            level = form.save()
            messages.success(request, f'Level {level.name} created successfully!')
            return redirect('academics:level_list')
    else:
        form = LevelForm()

    context = {
        'title': 'Create Level',
        'form': form,
    }
    return render(request, 'academics/level_form.html', context)


@login_required
@admin_required
def level_edit_view(request, pk):
    """Edit level"""
    level = get_object_or_404(Level, pk=pk)

    if request.method == 'POST':
        form = LevelForm(request.POST, instance=level)
        if form.is_valid():
            form.save()
            messages.success(request, f'Level {level.name} updated successfully!')
            return redirect('academics:level_list')
    else:
        form = LevelForm(instance=level)

    context = {
        'title': 'Edit Level',
        'form': form,
        'level': level,
    }
    return render(request, 'academics/level_form.html', context)


@login_required
@admin_required
def level_delete_view(request, pk):
    """Delete level"""
    level = get_object_or_404(Level, pk=pk)

    if request.method == 'POST':
        # Check if level has dependencies
        if level.students.exists():
            messages.error(request, 'Cannot delete level with existing students.')
            return redirect('academics:level_list')

        level_name = level.name
        level.delete()
        messages.success(request, f'Level {level_name} deleted successfully!')
        return redirect('academics:level_list')

    context = {
        'title': 'Delete Level',
        'level': level,
    }
    return render(request, 'academics/level_confirm_delete.html', context)


# ========================== AJAX VIEWS ==========================

@require_http_methods(["GET"])
def get_semesters_by_session_ajax(request):
    """Get semesters for a specific session"""
    session_id = request.GET.get('session_id')

    if not session_id:
        return JsonResponse({'semesters': []})

    semesters = Semester.objects.filter(
        session_id=session_id
    ).values('id', 'name', 'is_active')

    return JsonResponse({
        'semesters': list(semesters)
    })


@require_http_methods(["GET"])
def get_programs_by_department_ajax(request):
    """Get programs for a specific department"""
    department_id = request.GET.get('department_id')

    if not department_id:
        return JsonResponse({'programs': []})

    programs = Program.objects.filter(
        department_id=department_id
    ).values('id', 'name', 'duration_years')

    return JsonResponse({
        'programs': list(programs)
    })


@require_http_methods(["GET"])
def get_levels_by_program_ajax(request):
    """Get levels for a specific program"""
    program_id = request.GET.get('program_id')

    if not program_id:
        return JsonResponse({'levels': []})

    levels = Level.objects.filter(
        program_id=program_id
    ).values('id', 'name', 'order').order_by('order')

    return JsonResponse({
        'levels': list(levels)
    })


@login_required
@admin_required
@require_http_methods(["GET"])
def check_session_name_ajax(request):
    """Check if session name exists"""
    name = request.GET.get('name', '')
    session_id = request.GET.get('session_id', '')

    query = Session.objects.filter(name=name)
    if session_id:
        query = query.exclude(id=session_id)

    exists = query.exists()

    return JsonResponse({'exists': exists})