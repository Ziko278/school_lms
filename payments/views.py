from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from io import BytesIO

from .models import Payment
from .forms import PaymentFilterForm
from admin_site.models import SchoolInfo
from utils.decorators import admin_required


# ========================== PAYMENT MANAGEMENT VIEWS ==========================

@login_required
@admin_required
def payment_list_view(request):
    """List all payments"""
    payments = Payment.objects.select_related(
        'student__user', 'admitted_student'
    ).all().order_by('-created_at')

    # Filters
    form = PaymentFilterForm(request.GET)

    if form.is_valid():
        status = form.cleaned_data.get('status')
        if status:
            payments = payments.filter(status=status)

        payment_type = form.cleaned_data.get('payment_type')
        if payment_type:
            payments = payments.filter(payment_type=payment_type)

        date_from = form.cleaned_data.get('date_from')
        if date_from:
            payments = payments.filter(created_at__gte=date_from)

        date_to = form.cleaned_data.get('date_to')
        if date_to:
            payments = payments.filter(created_at__lte=date_to)

    # Search by reference
    search_query = request.GET.get('search', '')
    if search_query:
        payments = payments.filter(reference__icontains=search_query)

    # Statistics
    total_revenue = payments.filter(status='success').aggregate(
        total=Sum('amount')
    )['total'] or 0

    successful_count = payments.filter(status='success').count()
    pending_count = payments.filter(status='pending').count()
    failed_count = payments.filter(status='failed').count()

    # Pagination
    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    payments_page = paginator.get_page(page_number)

    context = {
        'title': 'Payments',
        'payments_page': payments_page,
        'form': form,
        'search_query': search_query,
        'total_revenue': total_revenue,
        'successful_count': successful_count,
        'pending_count': pending_count,
        'failed_count': failed_count,
    }
    return render(request, 'payments/payment_list.html', context)


@login_required
@admin_required
def payment_detail_view(request, pk):
    """View payment details"""
    payment = get_object_or_404(
        Payment.objects.select_related('student__user', 'admitted_student'),
        pk=pk
    )

    context = {
        'title': f'Payment - {payment.reference}',
        'payment': payment,
    }
    return render(request, 'payments/payment_detail.html', context)


@login_required
def payment_receipt_view(request, pk):
    """Generate payment receipt PDF"""
    payment = get_object_or_404(Payment, pk=pk)

    # Check permission
    if not request.user.is_superuser:
        if hasattr(request.user, 'profile') and request.user.profile.user_type != 'admin':
            if hasattr(request.user, 'student'):
                if payment.student != request.user.student:
                    messages.error(request, 'You do not have permission to view this receipt.')
                    return redirect('accounts:dashboard')
            else:
                messages.error(request, 'You do not have permission to view this receipt.')
                return redirect('accounts:dashboard')

    if payment.status != 'success':
        messages.error(request, 'Receipt can only be generated for successful payments.')
        return redirect('accounts:dashboard')

    school_info = SchoolInfo.get_instance()

    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    title_style = styles['Title']
    title_style.alignment = TA_CENTER
    elements.append(Paragraph(school_info.school_name, title_style))
    elements.append(Paragraph("PAYMENT RECEIPT", title_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Receipt details
    student_name = ''
    if payment.student:
        student_name = f"{payment.student.matric_number} - {payment.student.user.get_full_name()}"
    elif payment.admitted_student:
        student_name = f"{payment.admitted_student.first_name} {payment.admitted_student.last_name}"

    data = [
        ['Receipt Number:', payment.reference],
        ['Student:', student_name],
        ['Payment Type:', payment.get_payment_type_display()],
        ['Amount:', f'₦{payment.amount:,.2f}'],
        ['Payment Method:', payment.payment_method],
        ['Payment Date:', payment.payment_date.strftime('%Y-%m-%d %H:%M') if payment.payment_date else 'N/A'],
        ['Status:', payment.get_status_display()],
    ]

    table = Table(data, colWidths=[2 * inch, 4 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(
        Paragraph("This is a computer-generated receipt and does not require a signature.", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=receipt_{payment.reference}.pdf'

    return response


@login_required
@admin_required
def verify_payment_manually_view(request, pk):
    """Manually verify a failed/pending payment"""
    if request.method == 'POST':
        payment = get_object_or_404(Payment, pk=pk)

        # TODO: Re-verify with Paystack
        # For now, just mark as success

        payment.status = 'success'
        payment.payment_date = timezone.now()
        payment.save()

        messages.success(request, f'Payment {payment.reference} verified successfully.')
        return redirect('payments:payment_detail', pk=pk)

    return redirect('payments:payment_list')


# ========================== AJAX VIEWS ==========================

@require_http_methods(["POST"])
def verify_payment_reference_ajax(request):
    """Verify Paystack payment reference via AJAX"""
    try:
        reference = request.POST.get('reference')

        if not reference:
            return JsonResponse({
                'verified': False,
                'message': 'Reference is required'
            }, status=400)

        # TODO: Verify with Paystack API
        # For now, check database

        try:
            payment = Payment.objects.get(reference=reference)

            return JsonResponse({
                'verified': payment.status == 'success',
                'status': payment.status,
                'amount': float(payment.amount),
                'payment_date': payment.payment_date.isoformat() if payment.payment_date else None
            })
        except Payment.DoesNotExist:
            return JsonResponse({
                'verified': False,
                'message': 'Payment not found'
            }, status=404)

    except Exception as e:
        return JsonResponse({
            'verified': False,
            'message': str(e)
        }, status=500)


@login_required
@admin_required
@require_http_methods(["GET"])
def get_payment_stats_ajax(request):
    """Get payment statistics via AJAX"""
    try:
        total_payments = Payment.objects.count()
        successful = Payment.objects.filter(status='success').count()
        pending = Payment.objects.filter(status='pending').count()
        failed = Payment.objects.filter(status='failed').count()

        total_revenue = Payment.objects.filter(status='success').aggregate(
            total=Sum('amount')
        )['total'] or 0

        # Revenue by type
        revenue_by_type = {}
        for payment_type, display in Payment.PAYMENT_TYPE_CHOICES:
            revenue = Payment.objects.filter(
                status='success',
                payment_type=payment_type
            ).aggregate(total=Sum('amount'))['total'] or 0
            revenue_by_type[display] = float(revenue)

        return JsonResponse({
            'success': True,
            'stats': {
                'total_payments': total_payments,
                'successful': successful,
                'pending': pending,
                'failed': failed,
                'total_revenue': float(total_revenue),
                'revenue_by_type': revenue_by_type,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)