from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    # Public Pages
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('admission-portal/', views.admission_portal_view, name='admission_portal'),
    path('faq/', views.faq_view, name='faq'),
    path('departments/', views.departments_view, name='departments'),
    path('programs/', views.programs_view, name='programs'),

    # AJAX Views
    path('ajax/subscribe-newsletter/', views.subscribe_newsletter_ajax, name='subscribe_newsletter_ajax'),
    path('ajax/submit-contact/', views.submit_contact_form_ajax, name='submit_contact_form_ajax'),
    path('ajax/latest-news/', views.get_latest_news_ajax, name='get_latest_news_ajax'),

]
