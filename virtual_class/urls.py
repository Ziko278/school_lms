from django.urls import path
from . import views

app_name = 'virtual_class'

urlpatterns = [
    # Lecturer - Recordings
    path('recordings/', views.recording_list_view, name='recording_list'),
    path('recordings/upload/', views.recording_upload_view, name='recording_upload'),
    path('recordings/edit/<int:pk>/', views.recording_edit_view, name='recording_edit'),
    path('recordings/delete/<int:pk>/', views.recording_delete_view, name='recording_delete'),

    # Student - Recordings
    path('student/recordings/', views.student_recording_list_view, name='student_recording_list'),
    path('student/recordings/<int:pk>/', views.student_recording_view_view, name='student_recording_view'),

    # Lecturer - Whiteboard
    path('whiteboard/', views.whiteboard_view, name='whiteboard'),
    path('whiteboard/save/', views.whiteboard_save_view, name='whiteboard_save'),
    path('whiteboard/list/', views.whiteboard_list_view, name='whiteboard_list'),
    path('whiteboard/load/<int:pk>/', views.whiteboard_load_view, name='whiteboard_load'),
    path('whiteboard/delete/<int:pk>/', views.whiteboard_delete_view, name='whiteboard_delete'),

    # Student - Whiteboard
    path('student/whiteboards/', views.student_whiteboard_list_view, name='student_whiteboard_list'),
    path('student/whiteboard/<int:pk>/', views.student_whiteboard_view_view, name='student_whiteboard_view'),

    # AJAX Views
    path('ajax/save-whiteboard/', views.save_whiteboard_ajax, name='save_whiteboard_ajax'),
    path('ajax/load-whiteboard/', views.load_whiteboard_ajax, name='load_whiteboard_ajax'),
    path('ajax/delete-recording/', views.delete_recording_ajax, name='delete_recording_ajax'),
    path('ajax/recording-stats/', views.get_recording_stats_ajax, name='recording_stats_ajax'),
]