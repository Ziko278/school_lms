from django.db import models


class ClassRecording(models.Model):
    """Recorded virtual classes"""

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
    """Whiteboard content for virtual classes"""

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