from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from properties.models import Property, PropertyRequest
from messaging.models import Conversation, Message
from favorites.models import Favorite
from reviews.models import Review
from notifications.models import Notification
from django.db.models import Q, Count, Avg, Sum, Min, Max
from django.contrib.auth import get_user_model

User = get_user_model()


def _get_platform_stats():
    """Return site-wide platform statistics for dashboard display."""
    all_properties = Property.objects.filter(
        status=Property.Status.AVAILABLE, is_approved=True
    )
    total_available = all_properties.count()

    # Province breakdown
    province_stats = list(
        all_properties.exclude(province='')
        .values('province')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Property type breakdown
    type_stats = list(
        all_properties.values('property_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    # Map display names
    type_display = dict(Property.PropertyType.choices)
    for t in type_stats:
        t['display'] = type_display.get(t['property_type'], t['property_type'])

    # Price stats
    price_agg = all_properties.aggregate(
        avg_price=Avg('price'),
        min_price=Min('price'),
        max_price=Max('price'),
    )

    # Top districts
    top_districts = list(
        all_properties.values('district')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    # Total registered users
    total_users = User.objects.filter(is_active=True).count()
    total_owners = User.objects.filter(role='owner', is_active=True).count()
    total_tenants = User.objects.filter(role='tenant', is_active=True).count()

    # Platform-wide counts
    total_rented = Property.objects.filter(status=Property.Status.RENTED).count()
    total_reviews = Review.objects.count()
    total_conversations = Conversation.objects.count()

    return {
        'platform_total_available': total_available,
        'platform_provinces': province_stats,
        'platform_type_stats': type_stats,
        'platform_avg_price': price_agg.get('avg_price'),
        'platform_min_price': price_agg.get('min_price'),
        'platform_max_price': price_agg.get('max_price'),
        'platform_top_districts': top_districts,
        'platform_total_users': total_users,
        'platform_total_owners': total_owners,
        'platform_total_tenants': total_tenants,
        'platform_total_rented': total_rented,
        'platform_total_reviews': total_reviews,
        'platform_total_conversations': total_conversations,
    }


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

    # Total conversations
    total_conversations = Conversation.objects.filter(tenant=user).count()

    # Favorites
    favorites_count = Favorite.objects.filter(user=user).count()
    favorite_properties = Favorite.objects.filter(
        user=user
    ).select_related('property', 'property__owner').order_by('-created_at')[:4]

    # My requests
    my_requests = PropertyRequest.objects.filter(
        requester=user
    ).select_related('property').order_by('-created_at')[:5]

    # Request status breakdown
    request_status_counts = dict(
        PropertyRequest.objects.filter(requester=user)
        .values_list('status')
        .annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    pending_requests_count = request_status_counts.get('pending', 0)
    approved_requests_count = request_status_counts.get('approved', 0)
    rejected_requests_count = request_status_counts.get('rejected', 0)
    total_requests_count = sum(request_status_counts.values())

    # Request type breakdown
    request_type_counts = dict(
        PropertyRequest.objects.filter(requester=user)
        .values_list('request_type')
        .annotate(count=Count('id'))
        .values_list('request_type', 'count')
    )

    # Unread notifications
    unread_notifications = Notification.objects.filter(
        user=user, is_read=False
    ).count()

    # Recent notifications list
    recent_notifications = Notification.objects.filter(
        user=user
    ).order_by('-created_at')[:5]

    # My reviews
    my_reviews = Review.objects.filter(
        reviewer=user
    ).select_related('property').order_by('-created_at')[:5]
    total_reviews_given = Review.objects.filter(reviewer=user).count()

    # Recently listed properties
    recent_properties = Property.objects.filter(
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).select_related('owner')[:6]

    context = {
        'conversations': conversations,
        'unread_count': unread_count,
        'total_conversations': total_conversations,
        'favorites_count': favorites_count,
        'favorite_properties': favorite_properties,
        'my_requests': my_requests,
        'pending_requests_count': pending_requests_count,
        'approved_requests_count': approved_requests_count,
        'rejected_requests_count': rejected_requests_count,
        'total_requests_count': total_requests_count,
        'request_type_counts': request_type_counts,
        'unread_notifications': unread_notifications,
        'recent_notifications': recent_notifications,
        'my_reviews': my_reviews,
        'total_reviews_given': total_reviews_given,
        'recent_properties': recent_properties,
    }
    context.update(_get_platform_stats())
    return render(request, 'dashboard/tenant.html', context)


def owner_dashboard(request):
    """Dashboard for property owners."""
    user = request.user

    # Owner's properties
    properties = Property.objects.filter(owner=user)
    total_properties = properties.count()
    available_count = properties.filter(status=Property.Status.AVAILABLE).count()
    rented_count = properties.filter(status=Property.Status.RENTED).count()
    unavailable_count = properties.filter(status=Property.Status.UNAVAILABLE).count()

    # Total views across all properties
    total_views = properties.aggregate(total=Sum('views_count'))['total'] or 0

    # Average rating and total reviews across all owner's properties
    owner_review_stats = Review.objects.filter(property__owner=user).aggregate(
        avg_rating=Avg('rating'),
        total_reviews=Count('id'),
    )
    avg_rating = owner_review_stats['avg_rating']
    if avg_rating:
        avg_rating = round(avg_rating, 1)
    total_reviews = owner_review_stats['total_reviews']

    # Total favorites on owner's properties
    total_favorites = Favorite.objects.filter(property__owner=user).count()

    # Total unique tenants who interacted
    total_inquiries = PropertyRequest.objects.filter(property__owner=user).count()

    # Property type breakdown for this owner's portfolio
    owner_type_stats = list(
        properties.values('property_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    type_display = dict(Property.PropertyType.choices)
    for t in owner_type_stats:
        t['display'] = type_display.get(t['property_type'], t['property_type'])

    # Owner's price range
    owner_price_stats = properties.aggregate(
        avg_price=Avg('price'),
        min_price=Min('price'),
        max_price=Max('price'),
    )

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

    total_conversations = Conversation.objects.filter(owner=user).count()

    # Property requests
    pending_requests = PropertyRequest.objects.filter(
        property__owner=user,
        status=PropertyRequest.RequestStatus.PENDING,
    ).count()

    approved_requests = PropertyRequest.objects.filter(
        property__owner=user,
        status=PropertyRequest.RequestStatus.APPROVED,
    ).count()

    rejected_requests = PropertyRequest.objects.filter(
        property__owner=user,
        status=PropertyRequest.RequestStatus.REJECTED,
    ).count()

    recent_requests = PropertyRequest.objects.filter(
        property__owner=user
    ).select_related('property', 'requester').order_by('-created_at')[:5]

    # Reviews on owner's properties
    recent_reviews = Review.objects.filter(
        property__owner=user
    ).select_related('property', 'reviewer').order_by('-created_at')[:5]

    # Recent notifications
    recent_notifications = Notification.objects.filter(
        user=user
    ).order_by('-created_at')[:5]
    unread_notifications = Notification.objects.filter(
        user=user, is_read=False
    ).count()

    context = {
        'properties': properties[:5],
        'total_properties': total_properties,
        'available_count': available_count,
        'rented_count': rented_count,
        'unavailable_count': unavailable_count,
        'total_views': total_views,
        'avg_rating': avg_rating,
        'total_reviews': total_reviews,
        'total_favorites': total_favorites,
        'total_inquiries': total_inquiries,
        'owner_type_stats': owner_type_stats,
        'owner_avg_price': owner_price_stats.get('avg_price'),
        'owner_min_price': owner_price_stats.get('min_price'),
        'owner_max_price': owner_price_stats.get('max_price'),
        'conversations': conversations,
        'unread_count': unread_count,
        'total_conversations': total_conversations,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
        'recent_requests': recent_requests,
        'recent_reviews': recent_reviews,
        'recent_notifications': recent_notifications,
        'unread_notifications': unread_notifications,
    }
    context.update(_get_platform_stats())
    return render(request, 'dashboard/owner.html', context)
