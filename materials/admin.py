from django.contrib import admin
from .models import ClassMaterial, Assignment, AssignmentSubmission


@admin.register(ClassMaterial)
class ClassMaterialAdmin(admin.ModelAdmin):
    list_display = ['title', 'course_allocation', 'material_type', 'uploaded_at']
    list_filter = ['material_type']
    search_fields = ['title', 'course_allocation__course__code']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course_allocation', 'due_date', 'total_marks']
    search_fields = ['title', 'course_allocation__course__code']


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'assignment', 'submitted_at', 'score', 'graded_at']
    list_filter = ['graded_at']
    search_fields = ['student__matric_number', 'assignment__title']