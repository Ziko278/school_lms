from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    # Sessions
    path('sessions/', views.session_list_view, name='session_list'),
    path('sessions/create/', views.session_create_view, name='session_create'),
    path('sessions/<int:pk>/edit/', views.session_edit_view, name='session_edit'),
    path('sessions/<int:pk>/delete/', views.session_delete_view, name='session_delete'),
    path('sessions/<int:pk>/activate/', views.session_activate_view, name='session_activate'),

    # Semesters
    path('semesters/', views.semester_list_view, name='semester_list'),
    path('semesters/create/', views.semester_create_view, name='semester_create'),
    path('semesters/<int:pk>/edit/', views.semester_edit_view, name='semester_edit'),
    path('semesters/<int:pk>/delete/', views.semester_delete_view, name='semester_delete'),
    path('semesters/<int:pk>/activate/', views.semester_activate_view, name='semester_activate'),

    # Departments
    path('departments/', views.department_list_view, name='department_list'),
    path('departments/create/', views.department_create_view, name='department_create'),
    path('departments/<int:pk>/', views.department_detail_view, name='department_detail'),
    path('departments/<int:pk>/edit/', views.department_edit_view, name='department_edit'),
    path('departments/<int:pk>/delete/', views.department_delete_view, name='department_delete'),

    # Programs
    path('programs/', views.program_list_view, name='program_list'),
    path('programs/create/', views.program_create_view, name='program_create'),
    path('programs/<int:pk>/', views.program_detail_view, name='program_detail'),
    path('programs/<int:pk>/edit/', views.program_edit_view, name='program_edit'),
    path('programs/<int:pk>/delete/', views.program_delete_view, name='program_delete'),

    # Levels
    path('levels/', views.level_list_view, name='level_list'),
    path('levels/create/', views.level_create_view, name='level_create'),
    path('levels/<int:pk>/edit/', views.level_edit_view, name='level_edit'),
    path('levels/<int:pk>/delete/', views.level_delete_view, name='level_delete'),

    # AJAX URLs
    path('ajax/get-semesters/', views.get_semesters_by_session_ajax, name='get_semesters_ajax'),
    path('ajax/get-programs/', views.get_programs_by_department_ajax, name='get_programs_ajax'),
    path('ajax/get-levels/', views.get_levels_by_program_ajax, name='get_levels_ajax'),
    path('ajax/check-session-name/', views.check_session_name_ajax, name='check_session_name_ajax'),
]