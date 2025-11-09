from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'amount', 'payment_type', 'status', 'payment_date']
    list_filter = ['status', 'payment_type']
    search_fields = ['reference']