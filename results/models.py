from django.db import models
from django.core.exceptions import ValidationError


class Result(models.Model):
    """Student results model"""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    GRADE_CHOICES = [
        ('A', 'A (Excellent)'),
        ('B', 'B (Very Good)'),
        ('C', 'C (Good)'),
        ('D', 'D (Fair)'),
        ('E', 'E (Pass)'),
        ('F', 'F (Fail)'),
    ]

    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='results')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='results')
    session = models.ForeignKey('academics.Session', on_delete=models.CASCADE, related_name='results')
    semester = models.ForeignKey('academics.Semester', on_delete=models.CASCADE, related_name='results')
    ca_score = models.DecimalField(max_digits=5, decimal_places=2, help_text='Continuous Assessment (max 30 or 40)')
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, help_text='Exam score (max 70 or 60)')
    total_score = models.DecimalField(max_digits=5, decimal_places=2, editable=False)
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES, editable=False)
    grade_point = models.DecimalField(max_digits=3, decimal_places=2, editable=False)
    remarks = models.TextField(blank=True)
    submitted_by = models.ForeignKey('accounts.Staff', on_delete=models.PROTECT, related_name='submitted_results')
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='verified_results')
    verified_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        verbose_name = 'Result'
        verbose_name_plural = 'Results'
        unique_together = ['student', 'course', 'session', 'semester']
        ordering = ['-session', '-semester', 'student']
        permissions = [
            ("can_verify_results", "Can verify results"),
            ("can_generate_reports", "Can generate reports"),
        ]

    def __str__(self):
        return f"{self.student.matric_number} - {self.course.code} ({self.session.name})"

    def clean(self):
        """Validate scores"""
        if self.ca_score < 0 or self.ca_score > 40:
            raise ValidationError('CA score must be between 0 and 40')
        if self.exam_score < 0 or self.exam_score > 60:
            raise ValidationError('Exam score must be between 0 and 60')

    def save(self, *args, **kwargs):
        # Auto-calculate total score
        self.total_score = self.ca_score + self.exam_score

        # Auto-calculate grade and grade point
        if self.total_score >= 70:
            self.grade = 'A'
            self.grade_point = 5.0
        elif self.total_score >= 60:
            self.grade = 'B'
            self.grade_point = 4.0
        elif self.total_score >= 50:
            self.grade = 'C'
            self.grade_point = 3.0
        elif self.total_score >= 45:
            self.grade = 'D'
            self.grade_point = 2.0
        elif self.total_score >= 40:
            self.grade = 'E'
            self.grade_point = 1.0
        else:
            self.grade = 'F'
            self.grade_point = 0.0

        super().save(*args, **kwargs)