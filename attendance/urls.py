from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Lecturer Views
    path('', views.attendance_list_view, name='attendance_list'),
    path('create/', views.attendance_create_view, name='attendance_create'),
    path('edit/<int:pk>/', views.attendance_edit_view, name='attendance_edit'),
    path('detail/<int:pk>/', views.attendance_detail_view, name='attendance_detail'),
    path('report/', views.attendance_report_view, name='attendance_report'),

    # Student Views
    path('my-attendance/', views.student_attendance_view, name='student_attendance'),

    # AJAX Views
    path('ajax/mark/', views.mark_attendance_ajax, name='mark_attendance_ajax'),
    path('ajax/update-status/', views.update_attendance_status_ajax, name='update_attendance_status_ajax'),
    path('ajax/stats/', views.get_attendance_stats_ajax, name='get_attendance_stats_ajax'),
]
