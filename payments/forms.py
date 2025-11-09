from django import forms
from .models import Payment


class PaymentVerificationForm(forms.Form):
    """Form for verifying Paystack payment"""
    reference = forms.CharField(
        max_length=100,
        widget=forms.HiddenInput()
    )


class PaymentFilterForm(forms.Form):
    """Form for filtering payment records"""
    status = forms.ChoiceField(
        choices=[('', 'All')] + Payment.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_type = forms.ChoiceField(
        choices=[('', 'All')] + Payment.PAYMENT_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )