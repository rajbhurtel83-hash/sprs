from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from favorites.models import Favorite
from properties.models import Property


@login_required
def favorites_list(request):
    """Display a paginated list of the current user's favorited properties."""
    favorites = Favorite.objects.filter(user=request.user).select_related(
        "property"
    ).order_by("-created_at")

    paginator = Paginator(favorites, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "favorites/favorites_list.html", {
        "page_obj": page_obj,
    })


@login_required
@require_POST
def toggle_favorite(request, property_id):
    """Toggle the favorite status of a property for the current user.

    Returns a JSON response indicating whether the favorite was added or
    removed, along with the updated total count of favorites for the property.
    """
    property_obj = get_object_or_404(Property, pk=property_id)

    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        property=property_obj,
    )

    if not created:
        favorite.delete()
        status = "removed"
    else:
        status = "added"

    count = Favorite.objects.filter(property=property_obj).count()

    return JsonResponse({"status": status, "count": count})


@login_required
def check_favorite(request, property_id):
    """Check whether the current user has favorited a given property.

    Returns a JSON response with an ``is_favorited`` boolean flag.
    """
    property_obj = get_object_or_404(Property, pk=property_id)

    is_favorited = Favorite.objects.filter(
        user=request.user,
        property=property_obj,
    ).exists()

    return JsonResponse({"is_favorited": is_favorited})
