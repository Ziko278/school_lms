from django.contrib import admin
from .models import ClassRecording, Whiteboard


@admin.register(ClassRecording)
class ClassRecordingAdmin(admin.ModelAdmin):
    list_display = ['title', 'course_allocation', 'date_recorded', 'duration']
    list_filter = ['date_recorded']
    search_fields = ['title', 'course_allocation__course__code']


@admin.register(Whiteboard)
class WhiteboardAdmin(admin.ModelAdmin):
    list_display = ['title', 'course_allocation', 'session', 'semester', 'updated_at']
    list_filter = ['session', 'semester']
    search_fields = ['title', 'course_allocation__course__code']