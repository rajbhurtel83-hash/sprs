from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from properties.models import Property, PropertyRequest
from messaging.models import Conversation, Message
from favorites.models import Favorite
from reviews.models import Review
from notifications.models import Notification
from django.db.models import Q


@login_required
def dashboard_index(request):
    """Route to appropriate dashboard based on user role."""
    user = request.user

    if user.is_admin_user:
        return redirect('adminpanel:dashboard')

    if user.is_owner:
        return owner_dashboard(request)

    return tenant_dashboard(request)


def tenant_dashboard(request):
    """Dashboard for tenants."""
    user = request.user

    # Recent conversations
    raw_conversations = Conversation.objects.filter(
        tenant=user
    ).select_related('property', 'owner').prefetch_related('messages')[:5]

    conversations = []
    for conv in raw_conversations:
        conversations.append({
            'conversation': conv,
            'other_user': conv.owner,
            'last_message': conv.last_message,
            'unread_count': conv.unread_count_for(user),
        })

    # Unread message count
    unread_count = Message.objects.filter(
        conversation__tenant=user,
        is_read=False,
    ).exclude(sender=user).count()

    # Favorites count
    favorites_count = Favorite.objects.filter(user=user).count()

    # My requests
    my_requests = PropertyRequest.objects.filter(
        requester=user
    ).select_related('property').order_by('-created_at')[:5]

    # Unread notifications
    unread_notifications = Notification.objects.filter(
        user=user, is_read=False
    ).count()

    # Recently listed properties
    recent_properties = Property.objects.filter(
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).select_related('owner')[:6]

    context = {
        'conversations': conversations,
        'unread_count': unread_count,
        'favorites_count': favorites_count,
        'my_requests': my_requests,
        'unread_notifications': unread_notifications,
        'recent_properties': recent_properties,
    }
    return render(request, 'dashboard/tenant.html', context)


def owner_dashboard(request):
    """Dashboard for property owners."""
    user = request.user

    # Owner's properties
    properties = Property.objects.filter(owner=user)
    total_properties = properties.count()
    available_count = properties.filter(status=Property.Status.AVAILABLE).count()
    rented_count = properties.filter(status=Property.Status.RENTED).count()

    # Total views across all properties
    total_views = sum(p.views_count for p in properties)

    # Recent conversations
    raw_conversations = Conversation.objects.filter(
        owner=user
    ).select_related('property', 'tenant').prefetch_related('messages')[:5]

    conversations = []
    for conv in raw_conversations:
        conversations.append({
            'conversation': conv,
            'other_user': conv.tenant,
            'last_message': conv.last_message,
            'unread_count': conv.unread_count_for(user),
        })

    # Unread message count
    unread_count = Message.objects.filter(
        conversation__owner=user,
        is_read=False,
    ).exclude(sender=user).count()

    # Property requests
    pending_requests = PropertyRequest.objects.filter(
        property__owner=user,
        status=PropertyRequest.RequestStatus.PENDING,
    ).count()

    recent_requests = PropertyRequest.objects.filter(
        property__owner=user
    ).select_related('property', 'requester').order_by('-created_at')[:5]

    # Reviews on owner's properties
    recent_reviews = Review.objects.filter(
        property__owner=user
    ).select_related('property', 'reviewer').order_by('-created_at')[:5]

    context = {
        'properties': properties[:5],
        'total_properties': total_properties,
        'available_count': available_count,
        'rented_count': rented_count,
        'total_views': total_views,
        'conversations': conversations,
        'unread_count': unread_count,
        'pending_requests': pending_requests,
        'recent_requests': recent_requests,
        'recent_reviews': recent_reviews,
    }
    return render(request, 'dashboard/owner.html', context)
