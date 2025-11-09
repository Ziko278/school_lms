from django.urls import path
from . import views

app_name = 'results'

urlpatterns = [
    # Lecturer - Result Entry
    path('entry/', views.result_entry_list_view, name='result_entry_list'),
    path('entry/<int:allocation_id>/', views.result_entry_view, name='result_entry'),
    path('edit/<int:pk>/', views.result_edit_view, name='result_edit'),
    path('submit/<int:allocation_id>/', views.result_submit_view, name='result_submit'),

    # Admin - Result Verification
    path('verification/', views.result_verification_list_view, name='verification_list'),
    path('verify/<int:pk>/', views.result_verify_view, name='result_verify'),
    path('reject/<int:pk>/', views.result_reject_view, name='result_reject'),

    # Student - View Results
    path('my-results/', views.student_result_view, name='student_result'),
    path('transcript/', views.student_transcript_view, name='student_transcript'),
    path('result-slip/', views.result_slip_download_view, name='result_slip_download'),
    path('transcript-download/', views.transcript_download_view, name='transcript_download'),

    # AJAX Views
    path('ajax/save-result/', views.save_result_ajax, name='save_result_ajax'),
    path('ajax/verify-result/', views.verify_result_ajax, name='verify_result_ajax'),
    path('ajax/bulk-verify/', views.bulk_verify_results_ajax, name='bulk_verify_ajax'),
    path('ajax/result-stats/', views.get_result_stats_ajax, name='result_stats_ajax'),
    path('ajax/calculate-gpa/', views.calculate_gpa_ajax, name='calculate_gpa_ajax'),
    path('ajax/student-results/', views.get_student_results_ajax, name='student_results_ajax'),
]