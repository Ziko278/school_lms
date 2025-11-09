from django.db import models
from django.core.exceptions import ValidationError


class Course(models.Model):
    """Course model"""

    SEMESTER_CHOICES = [
        ('first', 'First Semester'),
        ('second', 'Second Semester'),
        ('both', 'Both Semesters'),
    ]

    code = models.CharField(max_length=20, unique=True, help_text='e.g., CSC 101')
    title = models.CharField(max_length=200)
    credit_units = models.IntegerField()
    department = models.ForeignKey('academics.Department', on_delete=models.CASCADE, related_name='courses')
    level = models.ForeignKey('academics.Level', on_delete=models.CASCADE, related_name='courses')
    semester_offered = models.CharField(max_length=20, choices=SEMESTER_CHOICES, default='first')
    description = models.TextField(blank=True)
    is_elective = models.BooleanField(default=False)
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='required_for')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.title}"


class CourseAllocation(models.Model):
    """Course allocation to lecturers"""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='allocations')
    lecturer = models.ForeignKey('accounts.Staff', on_delete=models.CASCADE, related_name='allocated_courses')
    session = models.ForeignKey('academics.Session', on_delete=models.CASCADE, related_name='course_allocations')
    semester = models.ForeignKey('academics.Semester', on_delete=models.CASCADE, related_name='course_allocations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Course Allocation'
        verbose_name_plural = 'Course Allocations'
        unique_together = ['course', 'session', 'semester']
        ordering = ['-session', '-semester', 'course']

    def __str__(self):
        return f"{self.course.code} - {self.lecturer.user.get_full_name()} ({self.session.name})"


class CourseRegistration(models.Model):
    """Student course registration"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='course_registrations')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='registrations')
    session = models.ForeignKey('academics.Session', on_delete=models.CASCADE, related_name='course_registrations')
    semester = models.ForeignKey('academics.Semester', on_delete=models.CASCADE, related_name='course_registrations')
    registration_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        verbose_name = 'Course Registration'
        verbose_name_plural = 'Course Registrations'
        unique_together = ['student', 'course', 'session', 'semester']
        ordering = ['-registration_date']
        permissions = [
            ("can_approve_course_registration", "Can approve course registration"),
        ]

    def __str__(self):
        return f"{self.student.matric_number} - {self.course.code} ({self.session.name})"