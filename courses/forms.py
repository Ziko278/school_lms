from django import forms
from .models import Course, CourseAllocation, CourseRegistration


class CourseForm(forms.ModelForm):
    """Form for creating/editing courses"""

    class Meta:
        model = Course
        fields = [
            'code', 'title', 'credit_units', 'department', 'level',
            'semester_offered', 'description', 'is_elective', 'prerequisites'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., CSC 101'
            }),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'credit_units': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control'}),
            'semester_offered': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_elective': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'prerequisites': forms.SelectMultiple(attrs={'class': 'form-control', 'size': 5}),
        }


class CourseAllocationForm(forms.ModelForm):
    """Form for allocating courses to lecturers"""

    class Meta:
        model = CourseAllocation
        fields = ['course', 'lecturer', 'session', 'semester']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'lecturer': forms.Select(attrs={'class': 'form-control'}),
            'session': forms.Select(attrs={'class': 'form-control'}),
            'semester': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter to show only staff members
        from accounts.models import Staff
        self.fields['lecturer'].queryset = Staff.objects.select_related('user').all()
        self.fields['lecturer'].label_from_instance = lambda obj: f"{obj.user.get_full_name()} ({obj.staff_id})"


class BulkCourseAllocationForm(forms.Form):
    """Form for bulk course allocation"""
    session = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    semester = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    department = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        help_text='Filter courses by department'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from academics.models import Session, Semester, Department
        self.fields['session'].queryset = Session.objects.all()
        self.fields['semester'].queryset = Semester.objects.all()
        self.fields['department'].queryset = Department.objects.all()


class CourseRegistrationForm(forms.ModelForm):
    """Form for students to register courses"""

    class Meta:
        model = CourseRegistration
        fields = ['course']
        widgets = {
            'course': forms.CheckboxSelectMultiple()
        }

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        if student:
            # Filter courses based on student's level and department
            self.fields['course'].queryset = Course.objects.filter(
                level=student.current_level,
                department=student.department
            )


class CourseRegistrationApprovalForm(forms.Form):
    """Form for approving/rejecting course registrations"""
    action = forms.ChoiceField(
        choices=[('approve', 'Approve'), ('reject', 'Reject')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    registration_ids = forms.CharField(
        widget=forms.HiddenInput()
    )