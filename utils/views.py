"""
Custom Error Handler Views
"""
from django.shortcuts import render


def handler404(request, exception):
    """Custom 404 error page"""
    context = {
        'title': 'Page Not Found',
    }
    return render(request, 'errors/404.html', context, status=404)


def handler500(request):
    """Custom 500 error page"""
    context = {
        'title': 'Server Error',
    }
    return render(request, 'errors/500.html', context, status=500)


def handler403(request, exception):
    """Custom 403 error page"""
    context = {
        'title': 'Permission Denied',
    }
    return render(request, 'errors/403.html', context, status=403)