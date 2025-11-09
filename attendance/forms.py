from django import forms
from .models import Attendance, AttendanceRecord


class AttendanceForm(forms.ModelForm):
    """Form for creating attendance session"""
    class Meta:
        model = Attendance
        fields = ['date', 'topic_covered']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'topic_covered': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AttendanceMarkingForm(forms.Form):
    """Form for marking attendance for multiple students"""
    def __init__(self, *args, students=None, **kwargs):
        super().__init__(*args, **kwargs)
        if students:
            for student in students:
                self.fields[f'student_{student.id}'] = forms.ChoiceField(
                    choices=AttendanceRecord.STATUS_CHOICES,
                    widget=forms.RadioSelect(),
                    label=f"{student.user.get_full_name()} ({student.matric_number})",
                    initial='present'
                )


class AttendanceRecordForm(forms.ModelForm):
    """Form for marking individual student attendance"""
    class Meta:
        model = AttendanceRecord
        fields = ['status']
        widgets = {
            'status': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        }


class AttendanceFilterForm(forms.Form):
    """Form for filtering attendance records"""
    course = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='All Courses'
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    def __init__(self, *args, lecturer=None, **kwargs):
        super().__init__(*args, **kwargs)
        if lecturer:
            from courses.models import CourseAllocation
            self.fields['course'].queryset = CourseAllocation.objects.filter(
                lecturer=lecturer
            ).select_related('course')
            self.fields['course'].label_from_instance = lambda obj: obj.course.code


class BulkAttendanceUpdateForm(forms.Form):
    """Form for bulk updating attendance status"""
    attendance_record_ids = forms.CharField(widget=forms.HiddenInput())
    new_status = forms.ChoiceField(
        choices=AttendanceRecord.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )