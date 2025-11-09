from django.db import models
from django.core.exceptions import ValidationError


class Session(models.Model):
    """Academic session model"""

    name = models.CharField(max_length=20, unique=True, help_text='e.g., 2024/2025')
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Session'
        verbose_name_plural = 'Sessions'
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def activate(self):
        """Activate this session and deactivate others"""
        Session.objects.all().update(is_active=False)
        self.is_active = True
        self.save()

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError('End date must be after start date')


class Semester(models.Model):
    """Semester model"""

    SEMESTER_CHOICES = [
        ('first', 'First Semester'),
        ('second', 'Second Semester'),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='semesters')
    name = models.CharField(max_length=20, choices=SEMESTER_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    registration_start_date = models.DateField(null=True, blank=True)
    registration_end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Semester'
        verbose_name_plural = 'Semesters'
        unique_together = ['session', 'name']
        ordering = ['-session', 'name']

    def __str__(self):
        return f"{self.session.name} - {self.get_name_display()}"

    def activate(self):
        """Activate this semester and deactivate others in the same session"""
        Semester.objects.filter(session=self.session).update(is_active=False)
        self.is_active = True
        self.save()

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError('End date must be after start date')


class Department(models.Model):
    """Department model"""

    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text='e.g., CSC, MTH')
    description = models.TextField(blank=True)
    hod = models.ForeignKey(
        'accounts.Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_department'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Program(models.Model):
    """Academic program model"""

    name = models.CharField(max_length=200, help_text='e.g., NCE Computer Science, B.Ed Mathematics')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='programs')
    duration_years = models.IntegerField(help_text='Program duration in years (e.g., 3, 4)')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Program'
        verbose_name_plural = 'Programs'
        ordering = ['department', 'name']

    def __str__(self):
        return f"{self.department.code} - {self.name}"


class Level(models.Model):
    """Academic level model"""

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='levels')
    name = models.CharField(max_length=50, help_text='e.g., NCE I, 100 Level')
    order = models.IntegerField(help_text='Level order: 1, 2, 3, 4')
    is_entry_level = models.BooleanField(default=False)
    is_exit_level = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Level'
        verbose_name_plural = 'Levels'
        unique_together = ['program', 'order']
        ordering = ['program', 'order']

    def __str__(self):
        return f"{self.program.name} - {self.name}"

    def clean(self):
        # Ensure only one entry level per program
        if self.is_entry_level:
            existing_entry = Level.objects.filter(
                program=self.program,
                is_entry_level=True
            ).exclude(pk=self.pk)
            if existing_entry.exists():
                raise ValidationError('Program already has an entry level')

        # Ensure only one exit level per program
        if self.is_exit_level:
            existing_exit = Level.objects.filter(
                program=self.program,
                is_exit_level=True
            ).exclude(pk=self.pk)
            if existing_exit.exists():
                raise ValidationError('Program already has an exit level')