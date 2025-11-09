from django.contrib import admin
from .models import SchoolInfo, SystemSettings


@admin.register(SchoolInfo)
class SchoolInfoAdmin(admin.ModelAdmin):
    list_display = ['school_name', 'school_email', 'school_phone', 'established_year']

    def has_add_permission(self, request):
        # Only allow one instance
        return not SchoolInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of singleton
        return False


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['registration_fee', 'current_session', 'current_semester', 'allow_student_registration']

    def has_add_permission(self, request):
        # Only allow one instance
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of singleton
        return False