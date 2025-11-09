from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings

from .forms import ContactForm, NewsletterSubscriptionForm
from admin_site.models import SchoolInfo, SystemSettings
from academics.models import Department, Program


# ========================== PUBLIC PAGES ==========================

def home_view(request):
    """Homepage"""
    school_info = SchoolInfo.get_instance()
    system_settings = SystemSettings.get_instance()

    # Get some statistics
    from accounts.models import Student, Staff
    total_students = Student.objects.count()
    total_staff = Staff.objects.count()
    total_departments = Department.objects.count()
    total_programs = Program.objects.count()

    context = {
        'title': 'Home',
        'school_info': school_info,
        'total_students': total_students,
        'total_staff': total_staff,
        'total_departments': total_departments,
        'total_programs': total_programs,
        'allow_registration': system_settings.allow_student_registration,
    }
    return render(request, 'website/home.html', context)


def about_view(request):
    """About page"""
    school_info = SchoolInfo.get_instance()

    context = {
        'title': 'About Us',
        'school_info': school_info,
    }
    return render(request, 'website/about.html', context)


def contact_view(request):
    """Contact page"""
    school_info = SchoolInfo.get_instance()

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # Send email
            try:
                full_message = f"""
                From: {name} ({email})

                {message}
                """

                send_mail(
                    f'Contact Form: {subject}',
                    full_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [school_info.school_email],
                    fail_silently=False,
                )

                messages.success(request, 'Your message has been sent successfully! We will get back to you soon.')
                return redirect('website:contact')
            except Exception as e:
                messages.error(request, 'Failed to send message. Please try again later.')
    else:
        form = ContactForm()

    context = {
        'title': 'Contact Us',
        'form': form,
        'school_info': school_info,
    }
    return render(request, 'website/contact.html', context)


def admission_portal_view(request):
    """Admission portal landing page"""
    school_info = SchoolInfo.get_instance()
    system_settings = SystemSettings.get_instance()

    # Get departments and programs
    departments = Department.objects.all()
    programs = Program.objects.select_related('department').all()

    context = {
        'title': 'Admission Portal',
        'school_info': school_info,
        'registration_fee': system_settings.registration_fee,
        'allow_registration': system_settings.allow_student_registration,
        'departments': departments,
        'programs': programs,
    }
    return render(request, 'website/admission_portal.html', context)


def faq_view(request):
    """FAQ page"""
    school_info = SchoolInfo.get_instance()

    # Define FAQs
    faqs = [
        {
            'question': 'How do I apply for admission?',
            'answer': 'Visit the Admission Portal, verify your JAMB details using your registration number and admission PIN, pay the registration fee, and complete the registration form.'
        },
        {
            'question': 'What is the registration fee?',
            'answer': f'The registration fee is ₦{SystemSettings.get_instance().registration_fee:,.2f}.'
        },
        {
            'question': 'How do I register for courses?',
            'answer': 'Login to your student portal, navigate to Course Registration, select your courses for the current semester, and submit for approval.'
        },
        {
            'question': 'How can I view my results?',
            'answer': 'Login to your student portal and navigate to Results section to view your verified results, GPA, and CGPA.'
        },
        {
            'question': 'What do I do if I forget my password?',
            'answer': 'Submit a password change request through the student portal. The admin will process your request and send you a new password via email.'
        },
        {
            'question': 'How do I download my admission letter?',
            'answer': 'After completing registration and payment, login to your student portal and navigate to the Admission Letter section to download your letter.'
        },
        {
            'question': 'How do I access course materials?',
            'answer': 'Login to your student portal, navigate to Course Materials, and you will see all materials uploaded by your lecturers for registered courses.'
        },
    ]

    context = {
        'title': 'Frequently Asked Questions',
        'school_info': school_info,
        'faqs': faqs,
    }
    return render(request, 'website/faq.html', context)


def departments_view(request):
    """List all departments"""
    school_info = SchoolInfo.get_instance()
    departments = Department.objects.all()

    context = {
        'title': 'Departments',
        'school_info': school_info,
        'departments': departments,
    }
    return render(request, 'website/departments.html', context)


def programs_view(request):
    """List all programs"""
    school_info = SchoolInfo.get_instance()
    programs = Program.objects.select_related('department').all()

    # Filter by department if provided
    department_id = request.GET.get('department')
    if department_id:
        programs = programs.filter(department_id=department_id)

    departments = Department.objects.all()

    context = {
        'title': 'Programs',
        'school_info': school_info,
        'programs': programs,
        'departments': departments,
        'selected_department': department_id,
    }
    return render(request, 'website/programs.html', context)


# ========================== AJAX VIEWS ==========================

@require_http_methods(["POST"])
def subscribe_newsletter_ajax(request):
    """Subscribe to newsletter via AJAX"""
    try:
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # TODO: Save to newsletter subscription model or send to mailing service
            # For now, just return success

            return JsonResponse({
                'success': True,
                'message': 'Thank you for subscribing to our newsletter!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Please enter a valid email address.'
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@require_http_methods(["POST"])
def submit_contact_form_ajax(request):
    """Submit contact form via AJAX"""
    try:
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            school_info = SchoolInfo.get_instance()

            # Send email
            full_message = f"""
            From: {name} ({email})

            {message}
            """

            send_mail(
                f'Contact Form: {subject}',
                full_message,
                settings.DEFAULT_FROM_EMAIL,
                [school_info.school_email],
                fail_silently=False,
            )

            return JsonResponse({
                'success': True,
                'message': 'Your message has been sent successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Please fill in all required fields correctly.',
                'errors': form.errors
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Failed to send message. Please try again later.'
        }, status=500)


@require_http_methods(["GET"])
def get_latest_news_ajax(request):
    """Get latest news items via AJAX"""
    # TODO: Implement news model and fetch latest news
    # For now, return empty array

    return JsonResponse({
        'success': True,
        'news': []
    })