from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('request-password-change/', views.request_password_change_view, name='request_password_change'),

    # Staff Management
    path('staff/', views.staff_list_view, name='staff_list'),
    path('staff/create/', views.staff_create_view, name='staff_create'),
    path('staff/<int:pk>/', views.staff_detail_view, name='staff_detail'),
    path('staff/<int:pk>/edit/', views.staff_edit_view, name='staff_edit'),
    path('staff/<int:pk>/delete/', views.staff_delete_view, name='staff_delete'),

    # Student Management
    path('students/', views.student_list_view, name='student_list'),
    path('students/<int:pk>/', views.student_detail_view, name='student_detail'),
    path('students/<int:pk>/edit/', views.student_edit_view, name='student_edit'),

    # Password Requests Management
    path('password-requests/', views.password_request_list_view, name='password_request_list'),
    path('password-requests/<int:pk>/approve/', views.password_request_approve_view, name='password_request_approve'),
    path('password-requests/<int:pk>/reject/', views.password_request_reject_view, name='password_request_reject'),

    # AJAX URLs
    path('ajax/check-username/', views.check_username_ajax, name='check_username_ajax'),
    path('ajax/check-email/', views.check_email_ajax, name='check_email_ajax'),
    path('ajax/update-profile-picture/', views.update_profile_picture_ajax, name='update_profile_picture_ajax'),
    path('ajax/staff-search/', views.staff_search_ajax, name='staff_search_ajax'),
    path('ajax/student-search/', views.student_search_ajax, name='student_search_ajax'),
    path('ajax/bulk-staff-action/', views.bulk_staff_action_ajax, name='bulk_staff_action_ajax'),
]