from django import forms
from .models import SchoolInfo, SystemSettings


class SchoolInfoForm(forms.ModelForm):
    """Form for editing school information"""
    class Meta:
        model = SchoolInfo
        fields = [
            'school_name', 'school_address', 'school_email',
            'school_phone', 'school_logo', 'school_website',
            'motto', 'established_year'
        ]
        widgets = {
            'school_name': forms.TextInput(attrs={'class': 'form-control'}),
            'school_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'school_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'school_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'school_logo': forms.FileInput(attrs={'class': 'form-control'}),
            'school_website': forms.URLInput(attrs={'class': 'form-control'}),
            'motto': forms.TextInput(attrs={'class': 'form-control'}),
            'established_year': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class SystemSettingsForm(forms.ModelForm):
    """Form for editing system settings"""
    class Meta:
        model = SystemSettings
        fields = [
            'registration_fee', 'matric_number_format', 'staff_id_format',
            'current_session', 'current_semester', 'allow_student_registration',
            'allow_course_registration', 'jamb_verification_enabled',
            'paystack_public_key', 'paystack_secret_key'
        ]
        widgets = {
            'registration_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'matric_number_format': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., COE/{YEAR}/{DEPT}/{SERIAL}'
            }),
            'staff_id_format': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., STAFF/{YEAR}/{SERIAL}'
            }),
            'current_session': forms.Select(attrs={'class': 'form-control'}),
            'current_semester': forms.Select(attrs={'class': 'form-control'}),
            'allow_student_registration': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_course_registration': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'jamb_verification_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'paystack_public_key': forms.TextInput(attrs={'class': 'form-control'}),
            'paystack_secret_key': forms.PasswordInput(attrs={'class': 'form-control'}),
        }