from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db.models import Q, Avg, F
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Property, PropertyImage, PropertyRequest
from .forms import PropertyForm, PropertyImageForm, PropertySearchForm, PropertyRequestForm
from users.decorators import owner_required
from reviews.forms import ReviewForm
from favorites.models import Favorite
from notifications.models import Notification


def property_list(request):
    """Public property listing with search and filters."""
    form = PropertySearchForm(request.GET)
    properties = Property.objects.filter(
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).select_related('owner').prefetch_related('images', 'reviews')

    if form.is_valid():
        keyword = form.cleaned_data.get('keyword')
        property_type = form.cleaned_data.get('property_type')
        district = form.cleaned_data.get('district')
        municipality = form.cleaned_data.get('municipality')
        ward_number = form.cleaned_data.get('ward_number')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')
        num_rooms = form.cleaned_data.get('num_rooms')
        rental_purpose = form.cleaned_data.get('rental_purpose')
        sort = form.cleaned_data.get('sort')

        if keyword:
            properties = properties.filter(
                Q(title__icontains=keyword) | Q(description__icontains=keyword)
            )
        if property_type:
            properties = properties.filter(property_type=property_type)
        if district:
            properties = properties.filter(district__icontains=district)
        if municipality:
            properties = properties.filter(municipality__icontains=municipality)
        if ward_number:
            properties = properties.filter(ward_number=ward_number)
        if min_price:
            properties = properties.filter(price__gte=min_price)
        if max_price:
            properties = properties.filter(price__lte=max_price)
        if num_rooms:
            properties = properties.filter(num_rooms__gte=num_rooms)
        if rental_purpose:
            properties = properties.filter(rental_purpose=rental_purpose)

        if sort == 'price_asc':
            properties = properties.order_by('price')
        elif sort == 'price_desc':
            properties = properties.order_by('-price')
        else:
            properties = properties.order_by('-created_at')

    paginator = Paginator(properties, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'properties': page_obj,
        'form': form,
        'total_count': paginator.count,
    }
    return render(request, 'properties/list.html', context)


def property_detail(request, pk):
    """Display detailed property information."""
    property_obj = get_object_or_404(
        Property.objects.select_related('owner').prefetch_related(
            'images', 'amenities', 'reviews__reviewer'
        ),
        pk=pk,
    )

    # Increment view count
    Property.objects.filter(pk=pk).update(views_count=F('views_count') + 1)

    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(
            user=request.user, property=property_obj
        ).exists()

    review_form = ReviewForm()
    request_form = PropertyRequestForm()

    # Google Maps API key for directions
    google_maps_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')

    from datetime import date
    context = {
        'property': property_obj,
        'is_favorited': is_favorited,
        'review_form': review_form,
        'request_form': request_form,
        'reviews': property_obj.reviews.select_related('reviewer')[:10],
        'google_maps_key': google_maps_key,
        'today_date': date.today().isoformat(),
    }
    return render(request, 'properties/detail.html', context)


def map_explorer(request):
    """Interactive map view with all properties - Premium version with Google Maps."""
    from django.conf import settings
    form = PropertySearchForm(request.GET)
    
    # Check if premium map should be used (when Google Maps API key is available)
    google_maps_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    
    context = {
        'form': form,
        'google_maps_key': google_maps_key,
    }
    
    # Use premium template if Google Maps API key is configured
    if google_maps_key:
        return render(request, 'properties/map_explorer_premium.html', context)
    else:
        # Fall back to Leaflet-based map
        return render(request, 'properties/map_explorer.html', context)


def map_explorer_legacy(request):
    """Legacy map explorer using Leaflet (OpenStreetMap)."""
    form = PropertySearchForm(request.GET)
    context = {
        'form': form,
        'google_maps_key': '',
    }
    return render(request, 'properties/map_explorer.html', context)


def property_compare(request):
    """Property comparison view - compare multiple properties side by side."""
    # Get property IDs from query params or session
    property_ids = request.GET.getlist('ids', [])
    
    # Also check session for comparison list
    if not property_ids:
        property_ids = request.session.get('compare_properties', [])
    
    # Limit to 4 properties max
    property_ids = property_ids[:4]
    
    properties = Property.objects.filter(
        pk__in=property_ids,
        status=Property.Status.AVAILABLE,
        is_approved=True
    ).select_related('owner').prefetch_related('images', 'amenities', 'reviews')
    
    # Get all unique amenities across selected properties
    all_amenities = set()
    for prop in properties:
        all_amenities.update(prop.amenities.values_list('name', flat=True))
    
    context = {
        'properties': properties,
        'all_amenities': sorted(all_amenities),
        'property_count': len(properties),
    }
    return render(request, 'properties/compare.html', context)


@login_required
def add_to_comparison(request, pk):
    """Add a property to comparison list (stored in session)."""
    from django.http import JsonResponse
    
    compare_list = request.session.get('compare_properties', [])
    
    if pk not in compare_list:
        if len(compare_list) >= 4:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Maximum 4 properties can be compared'
                })
            messages.warning(request, 'Maximum 4 properties can be compared at once.')
        else:
            compare_list.append(pk)
            request.session['compare_properties'] = compare_list
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'added',
                    'count': len(compare_list),
                    'message': 'Property added to comparison'
                })
            messages.success(request, 'Property added to comparison list.')
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'exists',
                'count': len(compare_list),
                'message': 'Property already in comparison'
            })
        messages.info(request, 'Property is already in your comparison list.')
    
    return redirect(request.META.get('HTTP_REFERER', 'properties:list'))


@login_required
def remove_from_comparison(request, pk):
    """Remove a property from comparison list."""
    from django.http import JsonResponse
    
    compare_list = request.session.get('compare_properties', [])
    
    if pk in compare_list:
        compare_list.remove(pk)
        request.session['compare_properties'] = compare_list
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'removed',
                'count': len(compare_list),
                'message': 'Property removed from comparison'
            })
        messages.success(request, 'Property removed from comparison list.')
    
    return redirect(request.META.get('HTTP_REFERER', 'properties:compare'))


@login_required
def clear_comparison(request):
    """Clear all properties from comparison list."""
    from django.http import JsonResponse
    
    request.session['compare_properties'] = []
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'cleared', 'count': 0})
    
    messages.success(request, 'Comparison list cleared.')
    return redirect('properties:list')


@login_required
@owner_required
def property_create(request):
    """Create a new property listing."""
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        image_form = PropertyImageForm(request.POST, request.FILES)

        if form.is_valid():
            property_obj = form.save(commit=False)
            property_obj.owner = request.user
            property_obj.save()
            form.save_m2m()  # Save amenities M2M

            # Handle multiple images
            images = request.FILES.getlist('images')
            for i, img in enumerate(images):
                PropertyImage.objects.create(
                    property=property_obj, image=img, is_primary=(i == 0)
                )

            # Handle single image from image_form
            if image_form.is_valid() and image_form.cleaned_data.get('image'):
                img_obj = image_form.save(commit=False)
                img_obj.property = property_obj
                if not images:
                    img_obj.is_primary = True
                img_obj.save()

            messages.success(request, 'Property listing created successfully.')
            return redirect('properties:detail', pk=property_obj.pk)
    else:
        form = PropertyForm()
        image_form = PropertyImageForm()

    return render(request, 'properties/create.html', {
        'form': form,
        'image_form': image_form,
    })


@login_required
@owner_required
def property_edit(request, pk):
    """Edit an existing property listing."""
    property_obj = get_object_or_404(Property, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = PropertyForm(request.POST, instance=property_obj)
        if form.is_valid():
            form.save()

            # Handle new images
            images = request.FILES.getlist('images')
            for img in images:
                PropertyImage.objects.create(property=property_obj, image=img)

            messages.success(request, 'Property listing updated successfully.')
            return redirect('properties:detail', pk=property_obj.pk)
    else:
        form = PropertyForm(instance=property_obj)

    return render(request, 'properties/edit.html', {
        'form': form,
        'property': property_obj,
    })


@login_required
@owner_required
def property_delete(request, pk):
    """Delete a property listing."""
    property_obj = get_object_or_404(Property, pk=pk, owner=request.user)

    if request.method == 'POST':
        property_obj.delete()
        messages.success(request, 'Property listing deleted successfully.')
        return redirect('dashboard:index')

    return render(request, 'properties/delete_confirm.html', {
        'property': property_obj,
    })


@login_required
@owner_required
def property_image_delete(request, pk):
    """Delete a property image."""
    image = get_object_or_404(PropertyImage, pk=pk, property__owner=request.user)
    property_pk = image.property.pk

    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Image deleted successfully.')

    return redirect('properties:edit', pk=property_pk)


@login_required
@owner_required
def my_properties(request):
    """List all properties owned by the current user."""
    properties = Property.objects.filter(owner=request.user).prefetch_related('images')

    paginator = Paginator(properties, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'properties/my_properties.html', {
        'properties': page_obj,
    })


@login_required
def submit_request(request, pk):
    """Submit a visit or inquiry request for a property."""
    property_obj = get_object_or_404(Property, pk=pk)

    if request.user == property_obj.owner:
        messages.error(request, "You cannot request your own property.")
        return redirect('properties:detail', pk=pk)

    if request.method == 'POST':
        form = PropertyRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.property = property_obj
            req.requester = request.user
            req.save()

            # Notify the owner
            Notification.objects.create(
                user=property_obj.owner,
                notification_type=Notification.NotificationType.REQUEST,
                title='New Property Request',
                message=f'{request.user.get_full_name() or request.user.username} sent a {req.get_request_type_display().lower()} request for "{property_obj.title}".',
                link=property_obj.get_absolute_url(),
            )

            messages.success(request, 'Your request has been submitted.')
            return redirect('properties:detail', pk=pk)

    return redirect('properties:detail', pk=pk)


@login_required
@owner_required
def manage_requests(request):
    """View and manage property requests for owner's properties."""
    requests_qs = PropertyRequest.objects.filter(
        property__owner=request.user
    ).select_related('property', 'requester').order_by('-created_at')

    paginator = Paginator(requests_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'properties/manage_requests.html', {
        'requests': page_obj,
    })


@login_required
@owner_required
def respond_request(request, pk):
    """Approve or reject a property request."""
    req = get_object_or_404(
        PropertyRequest, pk=pk, property__owner=request.user
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            req.status = PropertyRequest.RequestStatus.APPROVED
            notif_type = Notification.NotificationType.APPROVAL
            notif_title = 'Request Approved'
            notif_msg = f'Your {req.get_request_type_display().lower()} request for "{req.property.title}" has been approved!'
        elif action == 'reject':
            req.status = PropertyRequest.RequestStatus.REJECTED
            notif_type = Notification.NotificationType.REJECTION
            notif_title = 'Request Rejected'
            notif_msg = f'Your {req.get_request_type_display().lower()} request for "{req.property.title}" has been rejected.'
        else:
            messages.error(request, 'Invalid action.')
            return redirect('properties:manage_requests')

        req.responded_at = timezone.now()
        req.save()

        Notification.objects.create(
            user=req.requester,
            notification_type=notif_type,
            title=notif_title,
            message=notif_msg,
            link=req.property.get_absolute_url(),
        )

        messages.success(request, f'Request {req.status}.')
        return redirect('properties:manage_requests')
