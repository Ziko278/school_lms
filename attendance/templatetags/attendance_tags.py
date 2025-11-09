from django import template
register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def average_stats(course_stats_values):
    total = {'total': 0, 'present': 0, 'absent': 0, 'late': 0, 'percentage': 0, 'count': 0}
    if not course_stats_values:
        return total

    num_courses = len(course_stats_values)
    for stats in course_stats_values:
        total['total'] += stats.get('total', 0)
        total['present'] += stats.get('present', 0)
        total['absent'] += stats.get('absent', 0)
        total['late'] += stats.get('late', 0)
        total['percentage'] += stats.get('percentage', 0)
        total['count'] += 1 # Count courses with stats

    if total['count'] > 0:
        total['total'] /= total['count']
        total['present'] /= total['count']
        total['absent'] /= total['count']
        total['late'] /= total['count']
        total['percentage'] /= total['count'] # Average of percentages

    # Alternative: Recalculate overall percentage from avg present/total
    # avg_total_classes = total['total']
    # avg_present_classes = total['present']
    # if avg_total_classes > 0:
    #     total['percentage'] = (avg_present_classes / avg_total_classes) * 100
    # else:
    #     total['percentage'] = 0

    return total