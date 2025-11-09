from django.db import models


class Attendance(models.Model):
    """Attendance session for a class"""

    course_allocation = models.ForeignKey('courses.CourseAllocation', on_delete=models.CASCADE,
                                          related_name='attendances')
    date = models.DateField()
    topic_covered = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendances'
        unique_together = ['course_allocation', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.course_allocation.course.code} - {self.date}"

    def get_attendance_stats(self):
        """Get attendance statistics for this session"""
        total = self.records.count()
        present = self.records.filter(status='present').count()
        absent = self.records.filter(status='absent').count()
        late = self.records.filter(status='late').count()

        return {
            'total': total,
            'present': present,
            'absent': absent,
            'late': late,
            'percentage': (present / total * 100) if total > 0 else 0
        }


class AttendanceRecord(models.Model):
    """Individual student attendance record"""

    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]

    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        unique_together = ['attendance', 'student']
        ordering = ['-marked_at']

    def __str__(self):
        return f"{self.student.matric_number} - {self.attendance.date} ({self.status})"