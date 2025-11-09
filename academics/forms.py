from django import forms
from .models import Session, Semester, Department, Program, Level


class SessionForm(forms.ModelForm):
    """Form for creating/editing academic sessions"""
    class Meta:
        model = Session
        fields = ['name', 'start_date', 'end_date', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 2024/2025'
            }),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SemesterForm(forms.ModelForm):
    """Form for creating/editing semesters"""
    class Meta:
        model = Semester
        fields = [
            'session', 'name', 'start_date', 'end_date',
            'is_active', 'registration_start_date', 'registration_end_date'
        ]
        widgets = {
            'session': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'registration_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'registration_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class DepartmentForm(forms.ModelForm):
    """Form for creating/editing departments"""
    class Meta:
        model = Department
        fields = ['name', 'code', 'description', 'hod']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., CSC, MTH'
            }),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'hod': forms.Select(attrs={'class': 'form-control'}),
        }


class ProgramForm(forms.ModelForm):
    """Form for creating/editing programs"""
    class Meta:
        model = Program
        fields = ['name', 'department', 'duration_years', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., NCE Computer Science'
            }),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'duration_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class LevelForm(forms.ModelForm):
    """Form for creating/editing levels"""
    class Meta:
        model = Level
        fields = ['program', 'name', 'order', 'is_entry_level', 'is_exit_level']
        widgets = {
            'program': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., NCE I, 100 Level'
            }),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_entry_level': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_exit_level': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        