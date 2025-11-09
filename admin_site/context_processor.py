from admin_site.models import SchoolInfo


def general_info(request):
    site_info = SchoolInfo.objects.first()

    return {
        'site_info': site_info,
    }
