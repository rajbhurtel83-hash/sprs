from django.shortcuts import render
from django.db.models import Avg, Count
from properties.models import Property
from users.models import User


def home_view(request):
    """Premium home page with featured properties, hero slideshow, and system stats."""
    
    # Featured properties (prioritize highly-rated and verified)
    featured_properties = Property.objects.filter(
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).select_related('owner').prefetch_related('images', 'reviews').annotate(
        avg_rating=Avg('reviews__rating'),
        review_count_num=Count('reviews')
    ).order_by('-avg_rating', '-views_count')[:6]
    
    # Recent properties
    recent_properties = Property.objects.filter(
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).select_related('owner').prefetch_related('images', 'reviews').order_by('-created_at')[:6]
    
    # Get user's favorite property IDs for the favorite button state
    user_favorites = []
    if request.user.is_authenticated:
        from favorites.models import Favorite
        user_favorites = list(Favorite.objects.filter(
            user=request.user
        ).values_list('property_id', flat=True))
    
    context = {
        'featured_properties': featured_properties,
        'recent_properties': recent_properties,
        'user_favorites': user_favorites,
        'property_count': Property.objects.filter(
            status=Property.Status.AVAILABLE, is_approved=True
        ).count(),
        'owner_count': User.objects.filter(role=User.Role.OWNER).count(),
        'tenant_count': User.objects.filter(role=User.Role.TENANT).count(),
        'district_count': Property.objects.filter(
            status=Property.Status.AVAILABLE, is_approved=True
        ).values('district').distinct().count(),
    }
    
    # Use premium template
    return render(request, 'home_premium.html', context)


def home_view_legacy(request):
    """Legacy home page (original design)."""
    recent_properties = Property.objects.filter(
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).select_related('owner').prefetch_related('images')[:6]

    context = {
        'recent_properties': recent_properties,
        'property_count': Property.objects.filter(
            status=Property.Status.AVAILABLE, is_approved=True
        ).count(),
        'owner_count': User.objects.filter(role=User.Role.OWNER).count(),
        'tenant_count': User.objects.filter(role=User.Role.TENANT).count(),
        'district_count': Property.objects.filter(
            status=Property.Status.AVAILABLE, is_approved=True
        ).values('district').distinct().count(),
    }
    return render(request, 'home.html', context)


def custom_404(request, exception):
    return render(request, 'errors/404.html', status=404)


def custom_500(request):
    return render(request, 'errors/500.html', status=500)
