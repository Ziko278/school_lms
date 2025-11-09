from django.contrib import admin
from .models import UserProfile, Staff, Student, ChangePasswordRequest


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'phone_number', 'gender', 'created_at']
    list_filter = ['user_type', 'gender']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'phone_number']


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'user', 'department', 'designation', 'date_of_employment']
    list_filter = ['department', 'designation']
    search_fields = ['staff_id', 'user__username', 'user__first_name', 'user__last_name']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['matric_number', 'user', 'department', 'program', 'current_level', 'admission_status']
    list_filter = ['admission_status', 'department', 'program', 'current_level']
    search_fields = ['matric_number', 'jamb_registration_number', 'user__username', 'user__first_name', 'user__last_name']


@admin.register(ChangePasswordRequest)
class ChangePasswordRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'requested_at', 'processed_by', 'processed_at']
    list_filter = ['status']
    search_fields = ['user__username']