from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Admin Views
    path('', views.payment_list_view, name='payment_list'),
    path('<int:pk>/', views.payment_detail_view, name='payment_detail'),
    path('<int:pk>/receipt/', views.payment_receipt_view, name='payment_receipt'),
    path('<int:pk>/verify/', views.verify_payment_manually_view, name='verify_payment_manually'),

    # AJAX Views
    path('ajax/verify-reference/', views.verify_payment_reference_ajax, name='verify_payment_reference_ajax'),
    path('ajax/stats/', views.get_payment_stats_ajax, name='get_payment_stats_ajax'),
]
