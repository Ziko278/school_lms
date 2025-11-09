from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.conf import settings as django_settings
import pandas as pd

from .models import AdmittedStudent
from .forms import ExcelUploadForm, JAMBVerificationForm, StudentRegistrationForm
from accounts.models import Student, UserProfile
from academics.models import Department, Program, Level
from courses.models import Course
from admin_site.models import SystemSettings, SchoolInfo
from payments.models import Payment
from utils.decorators import admin_required
from utils.helpers import (
    generate_matric_number, send_admission_email,
    send_student_credentials_email, generate_admission_pin
)


# ========================== ADMITTED STUDENTS MANAGEMENT ==========================

@login_required
@admin_required
def admitted_students_list_view(request):
    """List all admitted students"""
    admitted_students = AdmittedStudent.objects.select_related(
        'department', 'program', 'admission_session'
    ).all()

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        admitted_students = admitted_students.filter(
            Q(jamb_registration_number__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Filters
    status = request.GET.get('status', '')
    if status:
        admitted_students = admitted_students.filter(admission_status=status)

    department_id = request.GET.get('department', '')
    if department_id:
        admitted_students = admitted_students.filter(department_id=department_id)

    session_id = request.GET.get('session', '')
    if session_id:
        admitted_students = admitted_students.filter(admission_session_id=session_id)

    # Pagination
    paginator = Paginator(admitted_students, 20)
    page_number = request.GET.get('page')
    admitted_page = paginator.get_page(page_number)

    departments = Department.objects.all()
    from academics.models import Session
    sessions = Session.objects.all()

    context = {
        'title': 'Admitted Students',
        'admitted_page': admitted_page,
        'departments': departments,
        'sessions': sessions,
        'search_query': search_query,
        'selected_status': status,
        'selected_department': department_id,
        'selected_session': session_id,
        'status_choices': AdmittedStudent.STATUS_CHOICES,
    }
    return render(request, 'admissions/admitted_list.html', context)


@login_required
@admin_required
def upload_admitted_students_view(request):
    """Upload admitted students via Excel file"""
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            session = form.cleaned_data['session']

            try:
                # Read Excel file
                df = pd.read_excel(excel_file)

                created_count = 0
                error_count = 0
                errors = []

                for index, row in df.iterrows():
                    try:
                        # Get or validate department
                        department = Department.objects.get(code=row['Department'])

                        # Get or validate program
                        program = Program.objects.get(
                            name__icontains=row['Program'],
                            department=department
                        )

                        # Check if JAMB number already exists
                        if AdmittedStudent.objects.filter(
                                jamb_registration_number=row['JAMB_No']
                        ).exists():
                            errors.append(f"Row {index + 2}: JAMB number {row['JAMB_No']} already exists")
                            error_count += 1
                            continue

                        # Create admitted student
                        admitted_student = AdmittedStudent.objects.create(
                            jamb_registration_number=row['JAMB_No'],
                            first_name=row['First_Name'],
                            last_name=row['Last_Name'],
                            email=row['Email'],
                            phone_number=row['Phone'],
                            department=department,
                            program=program,
                            admission_session=session,
                            course_codes=row['Course_Codes'],
                        )

                        # Send admission email with PIN
                        try:
                            send_admission_email(admitted_student)
                        except Exception as e:
                            # Log email error but continue
                            errors.append(f"Row {index + 2}: Email failed for {row['JAMB_No']}")

                        created_count += 1

                    except Department.DoesNotExist:
                        errors.append(f"Row {index + 2}: Department '{row['Department']}' not found")
                        error_count += 1
                    except Program.DoesNotExist:
                        errors.append(f"Row {index + 2}: Program '{row['Program']}' not found")
                        error_count += 1
                    except Exception as e:
                        errors.append(f"Row {index + 2}: {str(e)}")
                        error_count += 1

                # Display results
                if created_count > 0:
                    messages.success(request, f'{created_count} student(s) uploaded successfully!')

                if error_count > 0:
                    messages.warning(request, f'{error_count} error(s) occurred. See details below.')
                    for error in errors[:10]:  # Show first 10 errors
                        messages.error(request, error)

                return redirect('admissions:admitted_list')

            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
    else:
        form = ExcelUploadForm()

    context = {
        'title': 'Upload Admitted Students',
        'form': form,
    }
    return render(request, 'admissions/upload_admitted.html', context)


@login_required
@admin_required
def admitted_student_detail_view(request, pk):
    """View admitted student details"""
    admitted_student = get_object_or_404(
        AdmittedStudent.objects.select_related('department', 'program', 'admission_session'),
        pk=pk
    )

    # Get payment records
    payments = Payment.objects.filter(admitted_student=admitted_student)

    context = {
        'title': f'Admitted Student - {admitted_student.first_name} {admitted_student.last_name}',
        'admitted_student': admitted_student,
        'payments': payments,
    }
    return render(request, 'admissions/admitted_detail.html', context)


@login_required
@admin_required
def resend_admission_email_view(request, pk):
    """Resend admission email to student"""
    if request.method == 'POST':
        admitted_student = get_object_or_404(AdmittedStudent, pk=pk)

        try:
            send_admission_email(admitted_student)
            messages.success(request, f'Admission email resent to {admitted_student.email}')
        except Exception as e:
            messages.error(request, f'Failed to send email: {str(e)}')

    return redirect('admissions:admitted_detail', pk=pk)


# ========================== PUBLIC ADMISSION PROCESS ==========================

def jamb_verification_view(request):
    """JAMB number and PIN verification (Public)"""
    settings = SystemSettings.get_instance()

    # Check if student registration is allowed
    if not settings.allow_student_registration:
        messages.warning(request, 'Student registration is currently closed.')
        return render(request, 'admissions/registration_closed.html')

    if request.method == 'POST':
        form = JAMBVerificationForm(request.POST)
        if form.is_valid():
            admitted_student = form.cleaned_data['admitted_student']

            # Store admitted student ID in session
            request.session['admitted_student_id'] = admitted_student.id

            # Redirect to payment initiation
            return redirect('admissions:payment_initiation')
    else:
        form = JAMBVerificationForm()

    school_info = SchoolInfo.get_instance()

    context = {
        'title': 'Verify Admission',
        'form': form,
        'school_info': school_info,
    }
    return render(request, 'admissions/jamb_verification.html', context)


def payment_initiation_view(request):
    """Show payment summary and initiate Paystack payment"""
    admitted_student_id = request.session.get('admitted_student_id')

    if not admitted_student_id:
        messages.error(request, 'Session expired. Please verify your admission again.')
        return redirect('admissions:jamb_verification')

    admitted_student = get_object_or_404(AdmittedStudent, id=admitted_student_id)
    settings = SystemSettings.get_instance()
    school_info = SchoolInfo.get_instance()

    # Check if already paid
    existing_payment = Payment.objects.filter(
        admitted_student=admitted_student,
        status='success'
    ).first()

    if existing_payment:
        messages.info(request, 'You have already completed payment. Please proceed to registration.')
        return redirect('admissions:student_registration_form')

    if request.method == 'POST':
        # Generate payment reference
        import uuid
        reference = f"REG-{uuid.uuid4().hex[:12].upper()}"

        # Create payment record
        payment = Payment.objects.create(
            admitted_student=admitted_student,
            amount=settings.registration_fee,
            reference=reference,
            payment_type='registration',
            status='pending'
        )

        # Store payment reference in session
        request.session['payment_reference'] = reference

        # Initialize Paystack payment
        # TODO: Implement Paystack integration
        # For now, redirect to callback (in production, redirect to Paystack)

        # Simulate payment (remove in production)
        messages.info(request, 'Redirecting to payment gateway...')
        return redirect('admissions:payment_callback')

    context = {
        'title': 'Payment',
        'admitted_student': admitted_student,
        'registration_fee': settings.registration_fee,
        'school_info': school_info,
    }
    return render(request, 'admissions/payment_initiation.html', context)


def payment_callback_view(request):
    """Handle Paystack payment callback"""
    reference = request.GET.get('reference') or request.session.get('payment_reference')

    if not reference:
        messages.error(request, 'Invalid payment reference.')
        return redirect('admissions:jamb_verification')

    # Get payment record
    try:
        payment = Payment.objects.get(reference=reference)
    except Payment.DoesNotExist:
        messages.error(request, 'Payment record not found.')
        return redirect('admissions:jamb_verification')

    # Verify payment with Paystack
    # TODO: Implement Paystack verification
    # For now, mark as successful (remove in production)

    if payment.status == 'pending':
        payment.status = 'success'
        payment.payment_date = timezone.now()
        payment.save()

    if payment.status == 'success':
        messages.success(request, 'Payment successful! Please complete your registration.')
        request.session['payment_verified'] = True
        return redirect('admissions:student_registration_form')
    else:
        messages.error(request, 'Payment verification failed. Please try again.')
        return redirect('admissions:payment_initiation')


def student_registration_form_view(request):
    """Student registration form after payment"""
    admitted_student_id = request.session.get('admitted_student_id')
    payment_verified = request.session.get('payment_verified')

    if not admitted_student_id or not payment_verified:
        messages.error(request, 'Please complete payment first.')
        return redirect('admissions:jamb_verification')

    admitted_student = get_object_or_404(AdmittedStudent, id=admitted_student_id)

    # Check if already registered
    if admitted_student.admission_status == 'completed':
        messages.info(request, 'You have already completed registration.')
        return render(request, 'admissions/registration_complete.html', {
            'admitted_student': admitted_student
        })

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Create User account
                username = admitted_student.jamb_registration_number
                password = admitted_student.jamb_registration_number  # Default password

                user = User.objects.create_user(
                    username=username,
                    email=admitted_student.email,
                    password=password,
                    first_name=admitted_student.first_name,
                    last_name=admitted_student.last_name
                )

                UserProfile.objects.create(user=user)

                # Update UserProfile
                profile = user.profile
                profile.phone_number = admitted_student.phone_number
                profile.date_of_birth = form.cleaned_data['date_of_birth']
                profile.gender = form.cleaned_data['gender']
                profile.address = form.cleaned_data['address']
                profile.profile_picture = form.cleaned_data['profile_picture']
                profile.user_type = 'student'
                profile.save()

                # Get entry level for program
                entry_level = Level.objects.filter(
                    program=admitted_student.program,
                    is_entry_level=True
                ).first()

                if not entry_level:
                    # Fallback to first level
                    entry_level = Level.objects.filter(
                        program=admitted_student.program
                    ).order_by('order').first()

                # Create Student record
                student = Student.objects.create(
                    user=user,
                    jamb_registration_number=admitted_student.jamb_registration_number,
                    admission_session=admitted_student.admission_session,
                    department=admitted_student.department,
                    program=admitted_student.program,
                    current_level=entry_level,
                    admission_status='admitted',
                    has_paid_registration_fee=True
                )

                # Generate matric number
                student.matric_number = generate_matric_number(student)
                student.save()

                # Update admitted student status
                admitted_student.admission_status = 'completed'
                admitted_student.save()

                # Send credentials email
                try:
                    send_student_credentials_email(student, password)
                except:
                    pass  # Don't fail if email fails

                # Clear session
                request.session.flush()

                # Assign to Student group
                from django.contrib.auth.models import Group
                student_group, created = Group.objects.get_or_create(name='Students')
                user.groups.add(student_group)

                messages.success(request,
                                 'Registration completed successfully! Check your email for login credentials.')

                context = {
                    'title': 'Registration Complete',
                    'student': student,
                    'username': username,
                    'password': password,
                }
                return render(request, 'admissions/registration_success.html', context)

            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
    else:
        form = StudentRegistrationForm()

    context = {
        'title': 'Complete Registration',
        'form': form,
        'admitted_student': admitted_student,
    }
    return render(request, 'admissions/registration_form.html', context)


@login_required
def admission_letter_download_view(request):
    """Generate and download admission letter PDF"""
    if not hasattr(request.user, 'student'):
        messages.error(request, 'Only students can download admission letters.')
        return redirect('accounts:dashboard')

    student = request.user.student
    school_info = SchoolInfo.get_instance()

    # TODO: Generate PDF using reportlab
    # For now, return a simple response

    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = styles['Title']
    title_style.alignment = TA_CENTER
    elements.append(Paragraph(school_info.school_name, title_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Letter content
    content = f"""
    <para align=center><b>ADMISSION LETTER</b></para>
    <para><br/></para>
    <para>Dear {student.user.get_full_name()},</para>
    <para><br/></para>
    <para>Congratulations! We are pleased to inform you that you have been offered admission to study 
    <b>{student.program.name}</b> in the <b>{student.department.name}</b> for the 
    <b>{student.admission_session.name}</b> academic session.</para>
    <para><br/></para>
    <para><b>Matriculation Number:</b> {student.matric_number}</para>
    <para><b>JAMB Registration Number:</b> {student.jamb_registration_number}</para>
    <para><b>Department:</b> {student.department.name}</para>
    <para><b>Program:</b> {student.program.name}</para>
    <para><b>Level:</b> {student.current_level.name}</para>
    <para><br/></para>
    <para>Please proceed to complete your course registration and report to your department.</para>
    <para><br/></para>
    <para>We wish you a successful academic journey.</para>
    <para><br/></para>
    <para>Yours faithfully,</para>
    <para><b>The Registrar</b></para>
    """

    elements.append(Paragraph(content, styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=admission_letter_{student.matric_number}.pdf'

    return response


# ========================== AJAX VIEWS ==========================

# Change decorator to GET
@require_http_methods(["GET"])
def verify_jamb_ajax(request):
    """Verify JAMB and PIN via AJAX (Using GET - NOT RECOMMENDED FOR PRODUCTION)"""
    try:
        # Get data from query parameters
        jamb_number = request.GET.get('jamb_registration_number') # Use request.GET and the input name
        admission_pin = request.GET.get('admission_pin')         # Use request.GET and the input name

        # Basic check if parameters are provided
        if not jamb_number or not admission_pin:
             return JsonResponse({
                'valid': False,
                'message': 'JAMB number and PIN are required.'
            }, status=400) # Still return 400 for missing data

        admitted_student = AdmittedStudent.objects.get(
            jamb_registration_number=jamb_number,
            admission_pin=admission_pin,
            admission_status='pending'
        )

        return JsonResponse({
            'valid': True,
            'data': {
                'name': f"{admitted_student.first_name} {admitted_student.last_name}",
                'email': admitted_student.email,
                'department': admitted_student.department.name,
                'program': admitted_student.program.name,
            }
        })
    except AdmittedStudent.DoesNotExist:
        return JsonResponse({
            'valid': False,
            'message': 'Invalid JAMB number or Admission PIN'
        }, status=400) # Keep 400 for invalid credentials
    except Exception as e:
        # Log the exception for debugging
        print(f"Error in verify_jamb_ajax: {e}")
        return JsonResponse({
            'valid': False,
            'message': 'An unexpected server error occurred.' # More generic message
        }, status=500)


@require_http_methods(["GET"])
def check_jamb_exists_ajax(request):
    """Check if JAMB number already exists"""
    jamb_number = request.GET.get('jamb_number', '')

    exists = AdmittedStudent.objects.filter(
        jamb_registration_number=jamb_number
    ).exists()

    return JsonResponse({'exists': exists})


@require_http_methods(["POST"])
def validate_payment_ajax(request):
    """Validate payment reference"""
    try:
        reference = request.POST.get('reference')

        payment = Payment.objects.get(reference=reference)

        return JsonResponse({
            'valid': payment.status == 'success',
            'amount': float(payment.amount),
            'status': payment.status
        })
    except Payment.DoesNotExist:
        return JsonResponse({
            'valid': False,
            'message': 'Payment not found'
        }, status=404)


@login_required
@admin_required
@require_http_methods(["GET"])
def get_admitted_student_stats_ajax(request):
    """Get admission statistics"""
    try:
        total = AdmittedStudent.objects.count()
        pending = AdmittedStudent.objects.filter(admission_status='pending').count()
        completed = AdmittedStudent.objects.filter(admission_status='completed').count()

        return JsonResponse({
            'success': True,
            'stats': {
                'total': total,
                'pending': pending,
                'completed': completed,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["GET", "POST"])
def verify_admission_view(request):
    """JAMB number and PIN verification for public checking (Public)"""
    school_info = SchoolInfo.get_instance()

    # For GET requests, render the template
    if request.method == "GET":
        context = {
            'title': 'Verify Admission',
            'school_info': school_info,
        }
        return render(request, 'admissions/verify_admission.html', context)

    # For POST requests, verify the admission
    if request.method == "POST":
        try:
            import json
            data = json.loads(request.body)
            jamb_number = data.get('jamb_number', '').strip()
            admission_pin = data.get('admission_pin', '').strip()

            if not jamb_number or not admission_pin:
                return JsonResponse({
                    'success': False,
                    'message': 'JAMB number and Admission PIN are required.'
                }, status=400)

            # Find admitted student with both JAMB and PIN
            try:
                admitted_student = AdmittedStudent.objects.select_related(
                    'department', 'program', 'admission_session'
                ).get(
                    jamb_registration_number=jamb_number,
                    admission_pin=admission_pin
                )
                request.session['admitted_student_id'] = admitted_student.id
                return JsonResponse({
                    'success': True,
                    'message': 'Admission verified successfully!',
                    'data': {
                        'name': f"{admitted_student.first_name} {admitted_student.last_name}",
                        'email': admitted_student.email,
                        'program': admitted_student.program.name,
                        'department': admitted_student.department.name,
                    }
                })

            except AdmittedStudent.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid JAMB number or Admission PIN.'
                }, status=404)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid request data.'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'An error occurred while verifying admission.'
            }, status=500)