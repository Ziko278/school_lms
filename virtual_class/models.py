from django.contrib.auth.models import User
from django.db import models
import uuid


class LiveSession(models.Model):
    """Live virtual class sessions"""

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live Now'),
        ('ended', 'Ended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_allocation = models.ForeignKey('courses.CourseAllocation', on_delete=models.CASCADE,
                                          related_name='live_sessions')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    # Agora credentials
    agora_channel_name = models.CharField(max_length=100, unique=True)
    agora_app_id = models.CharField(max_length=100, blank=True)

    # Whiteboard data
    whiteboard_content = models.JSONField(null=True, blank=True,
                                          help_text='Final whiteboard state after session')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Live Session'
        verbose_name_plural = 'Live Sessions'
        ordering = ['-scheduled_start']

    def __str__(self):
        return f"{self.course_allocation.course.code} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.agora_channel_name:
            # Generate unique channel name
            self.agora_channel_name = f"vc_{self.id.hex[:12]}"
        super().save(*args, **kwargs)


class SessionParticipant(models.Model):
    """Track who joined a live session"""

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Session Participant'
        verbose_name_plural = 'Session Participants'
        unique_together = ['session', 'user']

    def __str__(self):
        return f"{self.user.get_full_name()} in {self.session.title}"


class ClassRecording(models.Model):
    """Recorded virtual classes - KEPT FOR BACKWARDS COMPATIBILITY"""

    course_allocation = models.ForeignKey('courses.CourseAllocation', on_delete=models.CASCADE,
                                          related_name='recordings')
    title = models.CharField(max_length=200)
    recording_file = models.FileField(upload_to='class_recordings/', null=True, blank=True)
    recording_link = models.URLField(null=True, blank=True, help_text='External link (e.g., YouTube)')
    date_recorded = models.DateField()
    duration = models.CharField(max_length=20, help_text='e.g., 1h 30m')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Class Recording'
        verbose_name_plural = 'Class Recordings'
        ordering = ['-date_recorded']

    def __str__(self):
        return f"{self.course_allocation.course.code} - {self.title}"


class Whiteboard(models.Model):
    """Whiteboard content for virtual classes - KEPT FOR BACKWARDS COMPATIBILITY"""

    course_allocation = models.ForeignKey('courses.CourseAllocation', on_delete=models.CASCADE,
                                          related_name='whiteboards')
    session = models.ForeignKey('academics.Session', on_delete=models.CASCADE, related_name='whiteboards')
    semester = models.ForeignKey('academics.Semester', on_delete=models.CASCADE, related_name='whiteboards')
    title = models.CharField(max_length=200)
    content = models.JSONField(help_text='Whiteboard drawing data in JSON format')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Whiteboard'
        verbose_name_plural = 'Whiteboards'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.course_allocation.course.code} - {self.title}"