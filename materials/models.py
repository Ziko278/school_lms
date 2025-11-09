from django.db import models


class ClassMaterial(models.Model):
    """Course materials uploaded by lecturers"""

    MATERIAL_TYPE_CHOICES = [
        ('pdf', 'PDF Document'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('link', 'External Link'),
        ('document', 'Document'),
    ]

    course_allocation = models.ForeignKey('courses.CourseAllocation', on_delete=models.CASCADE,
                                          related_name='materials')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES)
    file = models.FileField(upload_to='course_materials/', null=True, blank=True)
    external_link = models.URLField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Class Material'
        verbose_name_plural = 'Class Materials'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.course_allocation.course.code} - {self.title}"


class Assignment(models.Model):
    """Assignments created by lecturers"""

    course_allocation = models.ForeignKey('courses.CourseAllocation', on_delete=models.CASCADE,
                                          related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    file = models.FileField(upload_to='assignments/', null=True, blank=True)
    due_date = models.DateTimeField()
    total_marks = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.course_allocation.course.code} - {self.title}"


class AssignmentSubmission(models.Model):
    """Student assignment submissions"""

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='assignment_submissions')
    file = models.FileField(upload_to='assignment_submissions/')
    submission_text = models.TextField(blank=True, help_text='Additional text submission')
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Assignment Submission'
        verbose_name_plural = 'Assignment Submissions'
        unique_together = ['assignment', 'student']
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.matric_number} - {self.assignment.title}"

    @property
    def is_late(self):
        """Check if submission was late"""
        return self.submitted_at > self.assignment.due_date