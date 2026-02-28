from .models import Notification


def notification_context(request):
    """Add unread notification count to every template context."""
    if request.user.is_authenticated:
        unread_notification_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
    else:
        unread_notification_count = 0
    return {'unread_notification_count': unread_notification_count}
