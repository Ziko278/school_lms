from django.contrib import admin
from .models import Course, CourseAllocation, CourseRegistration


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'credit_units', 'department', 'level', 'is_elective']
    list_filter = ['department', 'level', 'is_elective', 'semester_offered']
    search_fields = ['code', 'title']
    filter_horizontal = ['prerequisites']


@admin.register(CourseAllocation)
class CourseAllocationAdmin(admin.ModelAdmin):
    list_display = ['course', 'lecturer', 'session', 'semester']
    list_filter = ['session', 'semester']
    search_fields = ['course__code', 'lecturer__user__first_name', 'lecturer__user__last_name']


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'session', 'semester', 'status', 'registration_date']
    list_filter = ['status', 'session', 'semester']
    search_fields = ['student__matric_number', 'course__code']
    actions = ['approve_registrations', 'reject_registrations']

    def approve_registrations(self, request, queryset):
        queryset.update(status='approved')
        self.message_user(request, f'{queryset.count()} registration(s) approved')

    approve_registrations.short_description = 'Approve selected registrations'

    def reject_registrations(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f'{queryset.count()} registration(s) rejected')

    reject_registrations.short_description = 'Reject selected registrations'