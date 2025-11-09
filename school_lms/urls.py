"""
Main URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Website (Public Pages)
    path('', include('website.urls')),

    # Accounts (Authentication, Profile, User Management)
    path('accounts/', include('accounts.urls')),

    # Admissions (Student Admission Process)
    path('admissions/', include('admissions.urls')),

    # Admin Site (Admin Dashboard, Reports, Settings)
    path('admin-dashboard/', include('admin_site.urls')),

    # Academics (Sessions, Semesters, Departments, Programs, Levels)
    path('academics/', include('academics.urls')),

    # Courses (Course Management, Allocation, Registration)
    path('courses/', include('courses.urls')),

    # Payments (Payment Management)
    path('payments/', include('payments.urls')),

    # Attendance (Class Attendance)
    path('materials/', include('materials.urls')),

    path('attendance/', include('attendance.urls')),



    # Results (Result Entry, Verification, Transcripts)
    path('results/', include('results.urls')),

    # Virtual Class (Recordings, Whiteboard)
    path('virtual-class/', include('virtual_class.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = 'utils.views.handler404'
handler500 = 'utils.views.handler500'
handler403 = 'utils.views.handler403'