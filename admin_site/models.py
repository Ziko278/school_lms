from django.db import models
from django.core.exceptions import ValidationError


class SingletonModel(models.Model):
    """Abstract base class for singleton models"""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.pk and self.__class__.objects.exists():
            raise ValidationError(f'Only one {self.__class__.__name__} instance is allowed')
        return super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """Get or create the singleton instance"""
        instance, created = cls.objects.get_or_create(pk=1)
        return instance


class SchoolInfo(SingletonModel):
    """School information singleton"""

    school_name = models.CharField(max_length=200, default='College of Education')
    school_address = models.TextField(blank=True)
    school_email = models.EmailField(blank=True)
    school_phone = models.CharField(max_length=15, blank=True)
    school_logo = models.ImageField(upload_to='school/', blank=True, null=True)
    school_website = models.URLField(blank=True)
    motto = models.CharField(max_length=200, blank=True)
    established_year = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = 'School Information'
        verbose_name_plural = 'School Information'

    def __str__(self):
        return self.school_name


class SystemSettings(SingletonModel):
    """System settings singleton"""

    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)
    matric_number_format = models.CharField(
        max_length=100,
        default='COE/{YEAR}/{DEPT}/{SERIAL}',
        help_text='Use {YEAR}, {DEPT}, {SERIAL} as placeholders'
    )
    staff_id_format = models.CharField(
        max_length=100,
        default='STAFF/{YEAR}/{SERIAL}',
        help_text='Use {YEAR}, {SERIAL} as placeholders'
    )
    current_session = models.ForeignKey(
        'academics.Session',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_current_session'
    )
    current_semester = models.ForeignKey(
        'academics.Semester',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_current_semester'
    )
    allow_student_registration = models.BooleanField(default=True, help_text='Toggle student admission registration')
    allow_course_registration = models.BooleanField(default=True, help_text='Toggle course registration')
    jamb_verification_enabled = models.BooleanField(default=True)
    paystack_public_key = models.CharField(max_length=200, blank=True)
    paystack_secret_key = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'
        permissions = [
            ("can_manage_school_info", "Can manage school information"),
            ("can_manage_system_settings", "Can manage system settings"),
        ]

    def __str__(self):
        return 'System Settings'