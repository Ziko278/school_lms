from django import forms
from .models import ClassMaterial, Assignment, AssignmentSubmission


class ClassMaterialForm(forms.ModelForm):
    """Form for uploading course materials"""

    class Meta:
        model = ClassMaterial
        fields = ['title', 'description', 'material_type', 'file', 'external_link']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'material_type': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'external_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        material_type = cleaned_data.get('material_type')
        file = cleaned_data.get('file')
        external_link = cleaned_data.get('external_link')

        if material_type == 'link':
            if not external_link:
                raise forms.ValidationError('External link is required for link type materials')
        else:
            if not file:
                raise forms.ValidationError('File is required for this material type')

        return cleaned_data


class AssignmentForm(forms.ModelForm):
    """Form for creating assignments"""

    class Meta:
        model = Assignment
        fields = ['title', 'description', 'file', 'due_date', 'total_marks', 'course_allocation']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 100}),
        }


class AssignmentSubmissionForm(forms.ModelForm):
    """Form for students to submit assignments"""

    class Meta:
        model = AssignmentSubmission
        fields = ['file', 'submission_text']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'submission_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional: Add any additional notes or comments'
            }),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Validate file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size must not exceed 10MB')
        return file


class AssignmentGradingForm(forms.ModelForm):
    """Form for lecturers to grade assignments"""

    class Meta:
        model = AssignmentSubmission
        fields = ['score', 'feedback']
        widgets = {
            'score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.assignment:
            self.fields['score'].widget.attrs['max'] = float(self.instance.assignment.total_marks)


class BulkMaterialDeleteForm(forms.Form):
    """Form for bulk deleting materials"""
    material_ids = forms.CharField(widget=forms.HiddenInput())