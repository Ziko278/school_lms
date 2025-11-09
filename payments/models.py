from django.db import models


class Payment(models.Model):
    """Payment model for tracking student payments"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    PAYMENT_TYPE_CHOICES = [
        ('registration', 'Registration Fee'),
        ('school_fees', 'School Fees'),
        ('other', 'Other'),
    ]

    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='payments', null=True,
                                blank=True)
    admitted_student = models.ForeignKey('admissions.AdmittedStudent', on_delete=models.CASCADE,
                                         related_name='payments', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='registration')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, default='Paystack')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.amount} ({self.status})"