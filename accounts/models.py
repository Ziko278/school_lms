from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended user profile for additional information"""

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    USER_TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('student', 'Student'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.user_type}"


class Staff(models.Model):
    """Staff/Lecturer model"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff')
    staff_id = models.CharField(max_length=20, unique=True, editable=False)
    department = models.ForeignKey('academics.Department', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='staff_members')
    designation = models.CharField(max_length=50, help_text="e.g., Lecturer I, Lecturer II, HOD, Dean")
    date_of_employment = models.DateField()
    qualifications = models.TextField(blank=True, help_text="Academic qualifications")
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Staff'
        verbose_name_plural = 'Staff'
        permissions = [
            ("can_upload_materials", "Can upload course materials"),
            ("can_create_assignments", "Can create assignments"),
            ("can_grade_assignments", "Can grade assignments"),
            ("can_mark_attendance", "Can mark attendance"),
            ("can_submit_results", "Can submit results"),
            ("can_record_classes", "Can record classes"),
            ("can_use_whiteboard", "Can use whiteboard"),
            ("can_view_allocated_courses", "Can view allocated courses"),
            ("can_view_course_students", "Can view course students"),
            ("can_allocate_courses", "Can allocate courses"),
        ]

    def __str__(self):
        return f"{self.staff_id} - {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.staff_id:
            # Generate staff ID from SystemSettings format
            from admin_site.models import SystemSettings
            settings = SystemSettings.get_instance()
            # Will implement auto-generation logic later
            self.staff_id = f"STAFF/{self.pk or 'NEW'}"
        super().save(*args, **kwargs)


class Student(models.Model):
    """Student model"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('admitted', 'Admitted'),
        ('graduated', 'Graduated'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student')
    matric_number = models.CharField(max_length=20, unique=True, editable=False)
    jamb_registration_number = models.CharField(max_length=20, unique=True)
    admission_session = models.ForeignKey('academics.Session', on_delete=models.PROTECT,
                                          related_name='admitted_students')
    department = models.ForeignKey('academics.Department', on_delete=models.PROTECT, related_name='students')
    program = models.ForeignKey('academics.Program', on_delete=models.PROTECT, related_name='students')
    current_level = models.ForeignKey('academics.Level', on_delete=models.PROTECT, related_name='students')
    admission_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    has_paid_registration_fee = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    admission_letter = models.FileField(upload_to='admission_letters/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        permissions = [
            ("can_view_own_profile", "Can view own profile"),
            ("can_register_courses", "Can register courses"),
            ("can_view_materials", "Can view materials"),
            ("can_submit_assignments", "Can submit assignments"),
            ("can_view_results", "Can view results"),
            ("can_view_attendance", "Can view attendance"),
            ("can_request_password_change", "Can request password change"),
        ]

    def __str__(self):
        return f"{self.matric_number} - {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.matric_number:
            # Generate matric number from SystemSettings format
            from admin_site.models import SystemSettings
            settings = SystemSettings.get_instance()
            # Will implement auto-generation logic later
            self.matric_number = f"COE/{self.pk or 'NEW'}"
        super().save(*args, **kwargs)


class ChangePasswordRequest(models.Model):
    """Password change requests from students"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField()
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='processed_password_requests')

    class Meta:
        verbose_name = 'Password Change Request'
        verbose_name_plural = 'Password Change Requests'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.user.username} - {self.status}"


# # Signal to auto-create UserProfile when User is created
# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()