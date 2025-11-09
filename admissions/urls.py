from django.urls import path
from . import views

app_name = 'admissions'

urlpatterns = [
    # Admin Views
    path('list/', views.admitted_students_list_view, name='admitted_list'),
    path('upload/', views.upload_admitted_students_view, name='upload_admitted'),
    path('detail/<int:pk>/', views.admitted_student_detail_view, name='admitted_detail'),
    path('resend-email/<int:pk>/', views.resend_admission_email_view, name='resend_admission_email'),

    # Public Admission Process
    path('verify/', views.jamb_verification_view, name='jamb_verification'),
    path('payment/', views.payment_initiation_view, name='payment_initiation'),
    path('verify-admission/', views.verify_admission_view, name='verify_admission'),
    path('callback/', views.payment_callback_view, name='payment_callback'),
    path('register/', views.student_registration_form_view, name='student_registration_form'),

    # Student View
    path('admission-letter/', views.admission_letter_download_view, name='admission_letter_download'),

    # AJAX Views
    path('ajax/verify-jamb/', views.verify_jamb_ajax, name='verify_jamb_ajax'),
    path('ajax/check-jamb/', views.check_jamb_exists_ajax, name='check_jamb_exists_ajax'),
    path('ajax/validate-payment/', views.validate_payment_ajax, name='validate_payment_ajax'),
    path('ajax/stats/', views.get_admitted_student_stats_ajax, name='get_admitted_student_stats_ajax'),
]
