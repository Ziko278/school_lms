from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Course Management
    path('', views.course_list_view, name='course_list'),
    path('create/', views.course_create_view, name='course_create'),
    path('<int:pk>/', views.course_detail_view, name='course_detail'),
    path('<int:pk>/edit/', views.course_edit_view, name='course_edit'),
    path('<int:pk>/delete/', views.course_delete_view, name='course_delete'),

    # Course Allocation
    path('allocations/', views.course_allocation_list_view, name='allocation_list'),
    path('allocations/create/', views.course_allocation_create_view, name='allocation_create'),
    path('allocations/bulk/', views.course_allocation_bulk_view, name='allocation_bulk'),
    path('allocations/<int:pk>/delete/', views.course_allocation_delete_view, name='allocation_delete'),

    # Course Registration Management (Admin/Registry)
    path('registrations/', views.course_registration_list_view, name='registration_list'),
    path('registrations/<int:pk>/approve/', views.course_registration_approve_view, name='registration_approve'),
    path('registrations/<int:pk>/reject/', views.course_registration_reject_view, name='registration_reject'),
    path('registrations/bulk-approve/', views.course_registration_bulk_approve_view, name='registration_bulk_approve'),

    # Student Course Registration
    path('register/', views.student_course_registration_view, name='student_register'),
    path('my-courses/', views.student_registered_courses_view, name='student_registered_courses'),

    # Lecturer Views
    path('my-allocated-courses/', views.lecturer_allocated_courses_view, name='lecturer_allocated_courses'),

    # AJAX URLs
    path('ajax/get-courses-by-level/', views.get_courses_by_level_ajax, name='get_courses_by_level_ajax'),
    path('ajax/get-prerequisites/', views.get_course_prerequisites_ajax, name='get_prerequisites_ajax'),
    path('ajax/check-course-code/', views.check_course_code_ajax, name='check_course_code_ajax'),
    path('ajax/get-lecturers/', views.get_lecturers_by_department_ajax, name='get_lecturers_ajax'),
    path('ajax/approve-registration/', views.approve_registration_ajax, name='approve_registration_ajax'),
    path('ajax/reject-registration/', views.reject_registration_ajax, name='reject_registration_ajax'),
    path('ajax/bulk-approve/', views.bulk_approve_registrations_ajax, name='bulk_approve_ajax'),
    path('ajax/get-students-by-allocation/', views.get_students_by_allocation, name='ajax_get_students_by_allocation'),

]