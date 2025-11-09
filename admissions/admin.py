from django.contrib import admin
from .models import AdmittedStudent


@admin.register(AdmittedStudent)
class AdmittedStudentAdmin(admin.ModelAdmin):
    list_display = ['jamb_registration_number', 'first_name', 'last_name', 'department', 'program', 'admission_status', 'admission_pin']
    list_filter = ['admission_status', 'department', 'program']
    search_fields = ['jamb_registration_number', 'first_name', 'last_name', 'email']
    readonly_fields = ['admission_pin']