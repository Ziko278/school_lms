"""
Utility Helper Functions
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from admin_site.models import SystemSettings, SchoolInfo
import random
import string


# ========================== ID GENERATION ==========================

def generate_matric_number(student):
    """Generate matric number based on format in settings"""
    settings_obj = SystemSettings.get_instance()
    format_string = settings_obj.matric_number_format

    # Get year from admission session
    year = student.admission_session.name.split('/')[0]

    # Get department code
    dept_code = student.department.code

    # Get serial number (count of students in same dept + session)
    from accounts.models import Student
    serial = Student.objects.filter(
        department=student.department,
        admission_session=student.admission_session
    ).count()

    # Format: COE/{YEAR}/{DEPT}/{SERIAL}
    matric_number = format_string.replace('{YEAR}', year)
    matric_number = matric_number.replace('{DEPT}', dept_code)
    matric_number = matric_number.replace('{SERIAL}', str(serial).zfill(4))

    return matric_number


def generate_staff_id(staff):
    """Generate staff ID based on format in settings"""
    settings_obj = SystemSettings.get_instance()
    format_string = settings_obj.staff_id_format

    # Get current year
    from datetime import datetime
    year = str(datetime.now().year)

    # Get serial number
    from accounts.models import Staff
    serial = Staff.objects.count() + 1

    # Format: STAFF/{YEAR}/{SERIAL}
    staff_id = format_string.replace('{YEAR}', year)
    staff_id = staff_id.replace('{SERIAL}', str(serial).zfill(4))

    return staff_id


def generate_admission_pin(length=10):
    """Generate random admission PIN"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


# ========================== EMAIL FUNCTIONS ==========================

def send_admission_email(admitted_student):
    """Send admission email with PIN"""
    school_info = SchoolInfo.get_instance()
    settings_obj = SystemSettings.get_instance()

    subject = f'Admission to {school_info.school_name}'

    context = {
        'student': admitted_student,
        'school_info': school_info,
        'registration_fee': settings_obj.registration_fee,
    }

    message = render_to_string('emails/admission_email.html', context)

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [admitted_student.email],
        html_message=message,
        fail_silently=False,
    )


def send_student_credentials_email(student, password):
    """Send login credentials to new student"""
    school_info = SchoolInfo.get_instance()

    subject = f'Your Login Credentials - {school_info.school_name}'

    context = {
        'student': student,
        'username': student.matric_number,
        'password': password,
        'school_info': school_info,
    }

    message = render_to_string('emails/student_credentials_email.html', context)

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [student.user.email],
        html_message=message,
        fail_silently=False,
    )


def send_password_reset_email(user, new_password):
    """Send password reset email"""
    school_info = SchoolInfo.get_instance()

    subject = f'Password Reset - {school_info.school_name}'

    message = f"""
    Hello {user.get_full_name()},

    Your password has been reset.

    New Password: {new_password}

    Please login and change your password immediately.

    Best regards,
    {school_info.school_name}
    """

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


# ========================== GPA CALCULATION ==========================

def calculate_gpa(results):
    """Calculate GPA from results"""
    if not results:
        return 0.0

    total_points = sum(r.grade_point * r.course.credit_units for r in results)
    total_units = sum(r.course.credit_units for r in results)

    if total_units == 0:
        return 0.0

    return round(total_points / total_units, 2)


def calculate_cgpa(student):
    """Calculate CGPA for student"""
    from results.models import Result

    all_results = Result.objects.filter(
        student=student,
        status='verified'
    ).select_related('course')

    return calculate_gpa(all_results)


def get_grade_from_score(score):
    """Get grade and grade point from score"""
    if score >= 70:
        return 'A', 5.0
    elif score >= 60:
        return 'B', 4.0
    elif score >= 50:
        return 'C', 3.0
    elif score >= 45:
        return 'D', 2.0
    elif score >= 40:
        return 'E', 1.0
    else:
        return 'F', 0.0


# ========================== VALIDATION HELPERS ==========================

def validate_phone_number(phone):
    """Validate phone number format"""
    import re
    # Nigerian phone number pattern
    pattern = r'^(\+234|0)[789]\d{9}$'
    return bool(re.match(pattern, phone))


def validate_jamb_number(jamb_number):
    """Validate JAMB registration number format"""
    import re
    # JAMB format: 12345678AB (8 digits + 2 letters)
    pattern = r'^\d{8}[A-Z]{2}$'
    return bool(re.match(pattern, jamb_number.upper()))


# ========================== FILE HELPERS ==========================

def handle_uploaded_file(file, path):
    """Handle file upload with validation"""
    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024
    if file.size > max_size:
        raise ValueError('File size must not exceed 10MB')

    # Validate file type
    allowed_extensions = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png']
    file_extension = file.name.lower().split('.')[-1]

    if f'.{file_extension}' not in allowed_extensions:
        raise ValueError(f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}')

    return file


def get_file_extension(filename):
    """Get file extension from filename"""
    return filename.split('.')[-1].lower()


def format_file_size(bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"


# ========================== DATE HELPERS ==========================

def get_current_academic_session():
    """Get current academic session based on date"""
    from datetime import datetime
    from academics.models import Session

    today = datetime.now().date()

    try:
        session = Session.objects.filter(
            start_date__lte=today,
            end_date__gte=today,
            is_active=True
        ).first()
        return session
    except:
        return None


def get_current_semester():
    """Get current semester based on date"""
    from datetime import datetime
    from academics.models import Semester

    today = datetime.now().date()

    try:
        semester = Semester.objects.filter(
            start_date__lte=today,
            end_date__gte=today,
            is_active=True
        ).first()
        return semester
    except:
        return None


def format_date(date, format='%B %d, %Y'):
    """Format date to readable string"""
    if date:
        return date.strftime(format)
    return 'N/A'


# ========================== NUMBER FORMATTING ==========================

def format_currency(amount):
    """Format currency (Naira)"""
    return f"₦{amount:,.2f}"


def format_percentage(value, decimal_places=2):
    """Format percentage"""
    return f"{value:.{decimal_places}f}%"


# ========================== STATISTICS HELPERS ==========================

def calculate_attendance_percentage(present, total):
    """Calculate attendance percentage"""
    if total == 0:
        return 0.0
    return round((present / total) * 100, 2)


def calculate_pass_rate(pass_count, total):
    """Calculate pass rate"""
    if total == 0:
        return 0.0
    return round((pass_count / total) * 100, 2)


def get_grade_distribution(results):
    """Get grade distribution from results"""
    from collections import Counter

    grades = [r.grade for r in results]
    distribution = Counter(grades)

    return dict(distribution)


# ========================== PAGINATION HELPERS ==========================

def get_pagination_range(page, paginator, on_each_side=3):
    """Get smart pagination range"""
    page_range = []

    if paginator.num_pages <= 10:
        page_range = list(paginator.page_range)
    else:
        # Show first page
        page_range.append(1)

        # Show pages around current page
        start = max(2, page.number - on_each_side)
        end = min(paginator.num_pages - 1, page.number + on_each_side)

        if start > 2:
            page_range.append('...')

        page_range.extend(range(start, end + 1))

        if end < paginator.num_pages - 1:
            page_range.append('...')

        # Show last page
        page_range.append(paginator.num_pages)

    return page_range


# ========================== SEARCH HELPERS ==========================

def search_students(query):
    """Search students by name or matric number"""
    from django.db.models import Q
    from accounts.models import Student

    return Student.objects.filter(
        Q(matric_number__icontains=query) |
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(user__email__icontains=query)
    ).select_related('user', 'department', 'current_level')


def search_staff(query):
    """Search staff by name or staff ID"""
    from django.db.models import Q
    from accounts.models import Staff

    return Staff.objects.filter(
        Q(staff_id__icontains=query) |
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(user__email__icontains=query)
    ).select_related('user', 'department')


def search_courses(query):
    """Search courses by code or title"""
    from django.db.models import Q
    from courses.models import Course

    return Course.objects.filter(
        Q(code__icontains=query) |
        Q(title__icontains=query)
    ).select_related('department', 'level')


# ========================== RANDOM GENERATORS ==========================

def generate_random_password(length=10):
    """Generate random password"""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))


def generate_reference_number(prefix='REF'):
    """Generate unique reference number"""
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"