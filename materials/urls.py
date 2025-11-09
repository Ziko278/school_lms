from django.urls import path
from . import views

app_name = 'materials'

urlpatterns = [
    # Lecturer - Materials
    path('', views.material_list_view, name='material_list'),
    path('upload/', views.material_upload_view, name='material_upload'),
    path('<int:pk>/edit/', views.material_edit_view, name='material_edit'),
    path('<int:pk>/delete/', views.material_delete_view, name='material_delete'),

    # Student - Materials
    path('student/materials/', views.student_material_list_view, name='student_material_list'),
    path('student/materials/<int:pk>/download/', views.student_material_download_view,
         name='student_material_download'),

    # Lecturer - Assignments
    path('assignments/', views.assignment_list_view, name='assignment_list'),
    path('assignments/create/', views.assignment_create_view, name='assignment_create'),
    path('assignments/<int:pk>/edit/', views.assignment_edit_view, name='assignment_edit'),
    path('assignments/<int:pk>/delete/', views.assignment_delete_view, name='assignment_delete'),
    path('assignments/<int:pk>/submissions/', views.assignment_submissions_view, name='assignment_submissions'),
    path('submissions/<int:pk>/grade/', views.assignment_grading_view, name='assignment_grading'),

    # Student - Assignments
    path('student/assignments/', views.student_assignment_list_view, name='student_assignment_list'),
    path('student/assignments/<int:pk>/submit/', views.student_assignment_submit_view,
         name='student_assignment_submit'),
    path('student/submissions/<int:pk>/feedback/', views.student_assignment_view_feedback_view,
         name='student_assignment_view_feedback'),

    # AJAX URLs
    path('ajax/upload-material/', views.upload_material_ajax, name='upload_material_ajax'),
    path('ajax/delete-material/', views.delete_material_ajax, name='delete_material_ajax'),
    path('ajax/get-materials/', views.get_materials_by_course_ajax, name='get_materials_ajax'),
    path('ajax/grade-assignment/', views.grade_assignment_ajax, name='grade_assignment_ajax'),
    path('ajax/check-submission/', views.check_assignment_submission_ajax, name='check_submission_ajax'),
]