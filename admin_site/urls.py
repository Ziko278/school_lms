from django.urls import path
from . import views

app_name = 'admin_site'

urlpatterns = [
    # Dashboard
    path('', views.admin_dashboard_view, name='admin_dashboard'),

    # School Info & Settings
    path('school-info/', views.school_info_view, name='school_info'),
    path('system-settings/', views.system_settings_view, name='system_settings'),

    # Reports
    path('reports/', views.reports_dashboard_view, name='reports_dashboard'),
    path('reports/enrollment/', views.student_enrollment_report_view, name='enrollment_report'),
    path('reports/payments/', views.payment_report_view, name='payment_report'),
    path('reports/results/', views.result_statistics_view, name='result_statistics'),

    # AJAX URLs
    path('ajax/get-system-stats/', views.get_system_stats_ajax, name='get_system_stats_ajax'),
    path('ajax/toggle-registration/', views.toggle_registration_ajax, name='toggle_registration_ajax'),
    path('ajax/set-active-session/', views.set_active_session_ajax, name='set_active_session_ajax'),
    path('ajax/set-active-semester/', views.set_active_semester_ajax, name='set_active_semester_ajax'),
]