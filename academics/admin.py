from django.contrib import admin
from .models import Session, Semester, Department, Program, Level


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active']
    actions = ['activate_session']

    def activate_session(self, request, queryset):
        for session in queryset:
            session.activate()
        self.message_user(request, f'{queryset.count()} session(s) activated')

    activate_session.short_description = 'Activate selected sessions'


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ['session', 'name', 'start_date', 'end_date', 'is_active']
    list_filter = ['session', 'name', 'is_active']
    actions = ['activate_semester']

    def activate_semester(self, request, queryset):
        for semester in queryset:
            semester.activate()
        self.message_user(request, f'{queryset.count()} semester(s) activated')

    activate_semester.short_description = 'Activate selected semesters'


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'hod']
    search_fields = ['name', 'code']


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'duration_years']
    list_filter = ['department']
    search_fields = ['name']


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['program', 'name', 'order', 'is_entry_level', 'is_exit_level']
    list_filter = ['program', 'is_entry_level', 'is_exit_level']