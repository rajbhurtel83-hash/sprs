from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notifications_list(request):
    """Show all notifications for the authenticated user, paginated by 20."""
    notifications = Notification.objects.filter(user=request.user)
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    unread_notification_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()
    return render(request, 'notifications/notifications_list.html', {
        'page_obj': page_obj,
        'unread_notification_count': unread_notification_count,
    })


@login_required
@require_POST
def mark_read(request, pk):
    """Mark a single notification as read by primary key."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def mark_all_read(request):
    """Mark all of the user's notifications as read."""
    updated_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).update(is_read=True)
    return JsonResponse({'status': 'ok', 'count': updated_count})
