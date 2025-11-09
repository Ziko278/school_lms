from django.contrib import admin
from .models import Result


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'session', 'semester', 'total_score', 'grade', 'status']
    list_filter = ['status', 'grade', 'session', 'semester']
    search_fields = ['student__matric_number', 'course__code']
    readonly_fields = ['total_score', 'grade', 'grade_point']
    actions = ['verify_results', 'reject_results']

    def verify_results(self, request, queryset):
        for result in queryset:
            result.status = 'verified'
            result.verified_by = request.user.staff
            from django.utils import timezone
            result.verified_at = timezone.now()
            result.save()
        self.message_user(request, f'{queryset.count()} result(s) verified')

    verify_results.short_description = 'Verify selected results'

    def reject_results(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f'{queryset.count()} result(s) rejected')

    reject_results.short_description = 'Reject selected results'