from django import forms
from .models import Result
from django.forms import formset_factory


class ResultEntryForm(forms.ModelForm):
    """Form for entering individual student result"""

    class Meta:
        model = Result
        fields = ['ca_score', 'exam_score', 'remarks']
        widgets = {
            'ca_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 40,
                'step': '0.01'
            }),
            'exam_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 60,
                'step': '0.01'
            }),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class BulkResultEntryForm(forms.Form):
    """Form for entering results for multiple students"""

    def __init__(self, *args, students=None, **kwargs):
        super().__init__(*args, **kwargs)
        if students:
            for student in students:
                self.fields[f'ca_score_{student.id}'] = forms.DecimalField(
                    max_digits=5,
                    decimal_places=2,
                    min_value=0,
                    max_value=40,
                    required=False,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'placeholder': 'CA'
                    })
                )
                self.fields[f'exam_score_{student.id}'] = forms.DecimalField(
                    max_digits=5,
                    decimal_places=2,
                    min_value=0,
                    max_value=60,
                    required=False,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'placeholder': 'Exam'
                    })
                )
                self.fields[f'remarks_{student.id}'] = forms.CharField(
                    required=False,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'placeholder': 'Remarks'
                    })
                )


class ResultVerificationForm(forms.Form):
    """Form for verifying results"""
    result_ids = forms.CharField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=[('verify', 'Verify'), ('reject', 'Reject')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for rejection (if rejecting)'
        })
    )


class ResultFilterForm(forms.Form):
    """Form for filtering results"""
    session = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='All Sessions'
    )
    semester = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='All Semesters'
    )
    department = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='All Departments'
    )
    level = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='All Levels'
    )
    status = forms.ChoiceField(
        choices=[('', 'All')] + Result.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from academics.models import Session, Semester, Department, Level
        self.fields['session'].queryset = Session.objects.all()
        self.fields['semester'].queryset = Semester.objects.all()
        self.fields['department'].queryset = Department.objects.all()
        self.fields['level'].queryset = Level.objects.all()


class StudentResultSearchForm(forms.Form):
    """Form for searching student results"""
    matric_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Matric Number'
        })
    )
    session = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='All Sessions'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from academics.models import Session
        self.fields['session'].queryset = Session.objects.all()