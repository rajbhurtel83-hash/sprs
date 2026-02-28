from rest_framework import generics, filters, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Avg, Count
from properties.models import Property, Amenity
from .serializers import (
    PropertyListSerializer,
    PropertyDetailSerializer,
    MapPropertySerializer,
    AmenitySerializer,
)


class StandardPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50


class PropertyListAPIView(generics.ListAPIView):
    """API endpoint for listing properties with filtering."""
    serializer_class = PropertyListSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Property.objects.filter(
            status=Property.Status.AVAILABLE,
            is_approved=True,
        ).select_related('owner').prefetch_related('images', 'reviews')

        # Apply filters from query params
        params = self.request.query_params

        keyword = params.get('keyword')
        if keyword:
            qs = qs.filter(
                Q(title__icontains=keyword) | Q(description__icontains=keyword)
            )

        district = params.get('district')
        if district:
            qs = qs.filter(district__icontains=district)

        municipality = params.get('municipality')
        if municipality:
            qs = qs.filter(municipality__icontains=municipality)

        ward = params.get('ward_number')
        if ward:
            qs = qs.filter(ward_number=ward)

        prop_type = params.get('property_type')
        if prop_type:
            qs = qs.filter(property_type=prop_type)

        min_price = params.get('min_price')
        if min_price:
            qs = qs.filter(price__gte=min_price)

        max_price = params.get('max_price')
        if max_price:
            qs = qs.filter(price__lte=max_price)

        num_rooms = params.get('num_rooms')
        if num_rooms:
            qs = qs.filter(num_rooms__gte=num_rooms)

        rental_purpose = params.get('rental_purpose')
        if rental_purpose:
            qs = qs.filter(rental_purpose=rental_purpose)

        amenities = params.getlist('amenities')
        if amenities:
            for a in amenities:
                qs = qs.filter(amenities__name__icontains=a)

        # Sorting
        sort = params.get('sort', '-created_at')
        if sort == 'price_asc':
            qs = qs.order_by('price')
        elif sort == 'price_desc':
            qs = qs.order_by('-price')
        elif sort == 'newest':
            qs = qs.order_by('-created_at')
        elif sort == 'rating':
            qs = qs.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
        else:
            qs = qs.order_by('-created_at')

        return qs


class PropertyDetailAPIView(generics.RetrieveAPIView):
    """API endpoint for property details."""
    serializer_class = PropertyDetailSerializer
    queryset = Property.objects.filter(
        is_approved=True
    ).select_related('owner').prefetch_related('images', 'amenities', 'reviews')


@api_view(['GET'])
def map_properties(request):
    """Return all available properties for map display with enhanced filtering."""
    qs = Property.objects.filter(
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).select_related('owner').prefetch_related('images', 'reviews', 'amenities')

    # Location filters
    district = request.query_params.get('district')
    if district:
        qs = qs.filter(district__icontains=district)

    municipality = request.query_params.get('municipality')
    if municipality:
        qs = qs.filter(municipality__icontains=municipality)

    # Property type filter
    prop_type = request.query_params.get('property_type')
    if prop_type:
        qs = qs.filter(property_type=prop_type)

    # Price range filters
    min_price = request.query_params.get('min_price')
    if min_price:
        qs = qs.filter(price__gte=min_price)

    max_price = request.query_params.get('max_price')
    if max_price:
        qs = qs.filter(price__lte=max_price)

    # Room filter
    num_rooms = request.query_params.get('num_rooms')
    if num_rooms:
        qs = qs.filter(num_rooms__gte=num_rooms)

    # Rental purpose filter
    rental_purpose = request.query_params.get('rental_purpose')
    if rental_purpose:
        qs = qs.filter(rental_purpose=rental_purpose)

    # Rating filter
    min_rating = request.query_params.get('min_rating')
    if min_rating:
        qs = qs.filter(average_rating__gte=float(min_rating))

    # Bounding box filter for map viewport
    ne_lat = request.query_params.get('ne_lat')
    ne_lng = request.query_params.get('ne_lng')
    sw_lat = request.query_params.get('sw_lat')
    sw_lng = request.query_params.get('sw_lng')

    if all([ne_lat, ne_lng, sw_lat, sw_lng]):
        qs = qs.filter(
            latitude__gte=float(sw_lat),
            latitude__lte=float(ne_lat),
            longitude__gte=float(sw_lng),
            longitude__lte=float(ne_lng),
        )

    # Only return properties with coordinates for mapping
    has_coords = request.query_params.get('has_coords', 'true')
    if has_coords == 'true':
        qs = qs.exclude(latitude__isnull=True).exclude(longitude__isnull=True)

    # Sorting
    sort_by = request.query_params.get('sort', '-created_at')
    allowed_sorts = ['price', '-price', 'average_rating', '-average_rating', '-created_at', 'created_at']
    if sort_by in allowed_sorts:
        qs = qs.order_by(sort_by)

    # Limit results
    limit = min(int(request.query_params.get('limit', 200)), 500)

    serializer = MapPropertySerializer(qs[:limit], many=True, context={'request': request})
    return Response({
        'count': qs.count(),
        'properties': serializer.data
    })


@api_view(['GET'])
def amenities_list(request):
    """Return all available amenities."""
    amenities = Amenity.objects.all()
    serializer = AmenitySerializer(amenities, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def search_suggestions(request):
    """Return search suggestions for autocomplete."""
    q = request.query_params.get('q', '')
    if len(q) < 2:
        return Response([])

    districts = Property.objects.filter(
        district__icontains=q,
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).values_list('district', flat=True).distinct()[:5]

    municipalities = Property.objects.filter(
        municipality__icontains=q,
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).values_list('municipality', flat=True).distinct()[:5]

    titles = Property.objects.filter(
        title__icontains=q,
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).values_list('title', flat=True)[:5]

    suggestions = (
        [{'type': 'district', 'value': d} for d in districts] +
        [{'type': 'municipality', 'value': m} for m in municipalities if m] +
        [{'type': 'property', 'value': t} for t in titles]
    )

    return Response(suggestions[:10])
