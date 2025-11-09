from django import forms
from .models import AdmittedStudent
from accounts.models import UserProfile
import pandas as pd


class ExcelUploadForm(forms.Form):
    """Form for uploading admitted students Excel file"""
    excel_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls'
        }),
        help_text='Upload Excel file with columns: JAMB_No, First_Name, Last_Name, Email, Phone, Department, Program, Course_Codes'
    )
    session = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select admission session'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from academics.models import Session
        self.fields['session'].queryset = Session.objects.filter(is_active=True)

    def clean_excel_file(self):
        file = self.cleaned_data['excel_file']

        # Validate file extension
        if not file.name.endswith(('.xlsx', '.xls')):
            raise forms.ValidationError('Only Excel files (.xlsx, .xls) are allowed')

        # Validate file size (max 5MB)
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File size must not exceed 5MB')

        # Try to read the Excel file
        try:
            df = pd.read_excel(file)
            required_columns = [
                'JAMB_No', 'First_Name', 'Last_Name', 'Email',
                'Phone', 'Department', 'Program', 'Course_Codes'
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise forms.ValidationError(
                    f'Missing required columns: {", ".join(missing_columns)}'
                )
        except Exception as e:
            raise forms.ValidationError(f'Error reading Excel file: {str(e)}')

        return file


class JAMBVerificationForm(forms.Form):
    """Form for JAMB number and PIN verification"""
    jamb_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your JAMB Registration Number'
        })
    )
    admission_pin = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your Admission PIN'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        jamb_number = cleaned_data.get('jamb_number')
        admission_pin = cleaned_data.get('admission_pin')

        if jamb_number and admission_pin:
            try:
                admitted_student = AdmittedStudent.objects.get(
                    jamb_registration_number=jamb_number,
                    admission_pin=admission_pin,
                    admission_status='pending'
                )
                cleaned_data['admitted_student'] = admitted_student
            except AdmittedStudent.DoesNotExist:
                raise forms.ValidationError(
                    'Invalid JAMB number or Admission PIN, or registration already completed'
                )

        return cleaned_data


class StudentRegistrationForm(forms.Form):
    """Form for student to complete registration after payment"""
    # Personal Information
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    gender = forms.ChoiceField(
        choices=UserProfile.GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    profile_picture = forms.ImageField(
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='Upload passport photograph'
    )

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            # Validate file size (max 2MB)
            if picture.size > 2 * 1024 * 1024:
                raise forms.ValidationError('Image size must not exceed 2MB')

            # Validate file type
            if not picture.content_type.startswith('image/'):
                raise forms.ValidationError('Only image files are allowed')

        return picture