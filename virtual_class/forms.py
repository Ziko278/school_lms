from django import forms
from .models import LiveSession, ClassRecording, Whiteboard
from django.utils import timezone


class LiveSessionForm(forms.ModelForm):
    """Form for creating/editing live sessions"""

    class Meta:
        model = LiveSession
        fields = ['course_allocation', 'title', 'description', 'scheduled_start', 'scheduled_end']
        widgets = {
            'course_allocation': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'e.g., Lecture 5 - Data Structures'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Session description...'}),
            'scheduled_start': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'scheduled_end': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('scheduled_start')
        end = cleaned_data.get('scheduled_end')

        if start and end:
            if end <= start:
                raise forms.ValidationError('End time must be after start time')

            if start < timezone.now():
                raise forms.ValidationError('Start time cannot be in the past')

            # Check duration (max 4 hours)
            duration = (end - start).total_seconds() / 3600
            if duration > 4:
                raise forms.ValidationError('Session duration cannot exceed 4 hours')

        return cleaned_data


class ClassRecordingForm(forms.ModelForm):
    """Form for uploading class recordings - KEPT FOR BACKWARDS COMPATIBILITY"""

    class Meta:
        model = ClassRecording
        fields = ['title', 'recording_file', 'recording_link', 'date_recorded', 'duration', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'recording_file': forms.FileInput(attrs={'class': 'form-control'}),
            'recording_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., YouTube link'
            }),
            'date_recorded': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'duration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1h 30m'
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        recording_file = cleaned_data.get('recording_file')
        recording_link = cleaned_data.get('recording_link')

        if not recording_file and not recording_link:
            raise forms.ValidationError('Either upload a file or provide a recording link')

        return cleaned_data

    def clean_recording_file(self):
        file = self.cleaned_data.get('recording_file')
        if file:
            # Validate file size (max 500MB for videos)
            if file.size > 500 * 1024 * 1024:
                raise forms.ValidationError('Recording file size must not exceed 500MB')
        return file


class WhiteboardForm(forms.ModelForm):
    """Form for saving whiteboard content - KEPT FOR BACKWARDS COMPATIBILITY"""

    class Meta:
        model = Whiteboard
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.HiddenInput(),
        }


class WhiteboardLoadForm(forms.Form):
    """Form for loading existing whiteboard - KEPT FOR BACKWARDS COMPATIBILITY"""
    whiteboard = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Select a saved whiteboard'
    )

    def __init__(self, *args, course_allocation=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course_allocation:
            self.fields['whiteboard'].queryset = Whiteboard.objects.filter(
                course_allocation=course_allocation
            ).order_by('-updated_at')