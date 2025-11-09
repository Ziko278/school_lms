from django.db import models
import uuid


class AdmittedStudent(models.Model):
    """Temporary model for admitted students before full registration"""

    STATUS_CHOICES = [
        ('pending', 'Pending Registration'),
        ('completed', 'Registration Completed'),
        ('expired', 'Expired'),
    ]

    jamb_registration_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    department = models.ForeignKey('academics.Department', on_delete=models.CASCADE, related_name='admitted_students')
    program = models.ForeignKey('academics.Program', on_delete=models.CASCADE, related_name='admitted_students')
    admission_session = models.ForeignKey('academics.Session', on_delete=models.CASCADE, related_name='admissions')
    course_codes = models.TextField(help_text='Comma-separated course codes')
    admission_pin = models.CharField(max_length=20, unique=True, editable=False)
    admission_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Admitted Student'
        verbose_name_plural = 'Admitted Students'
        ordering = ['-created_at']
        permissions = [
            ("can_verify_student_admission", "Can verify student admission"),
            ("can_upload_admitted_students", "Can upload admitted students"),
        ]

    def __str__(self):
        return f"{self.jamb_registration_number} - {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.admission_pin:
            # Generate unique 10-character PIN
            self.admission_pin = str(uuid.uuid4().hex)[:10].upper()
        super().save(*args, **kwargs)

    def get_course_codes_list(self):
        """Return list of course codes"""
        return [code.strip() for code in self.course_codes.split(',') if code.strip()]