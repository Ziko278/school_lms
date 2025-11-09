from django.contrib import admin
from .models import Attendance, AttendanceRecord


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['course_allocation', 'date', 'topic_covered']
    list_filter = ['date']
    search_fields = ['course_allocation__course__code', 'topic_covered']


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'attendance', 'status', 'marked_at']
    list_filter = ['status']
    search_fields = ['student__matric_number']