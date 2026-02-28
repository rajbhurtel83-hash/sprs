from django.db.models import Q
from .models import Message


def unread_messages_count(request):
    """Context processor to add unread message count to all templates."""
    if request.user.is_authenticated:
        count = Message.objects.filter(
            Q(conversation__tenant=request.user) | Q(conversation__owner=request.user),
            is_read=False,
        ).exclude(sender=request.user).count()
        return {'unread_messages_count': count}
    return {'unread_messages_count': 0}
