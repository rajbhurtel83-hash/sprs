import logging

from rest_framework import generics, filters, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Avg, Count
import math
from properties.models import Property, Amenity
from properties.models import get_canonical_district_choices
from .serializers import (
    PropertyListSerializer,
    PropertyDetailSerializer,
    MapPropertySerializer,
    AmenitySerializer,
)


logger = logging.getLogger(__name__)


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

        province = params.get('province')
        if province:
            qs = qs.filter(province__iexact=province)

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

    keyword = request.query_params.get('keyword')
    location_query = request.query_params.get('location_query')

    if keyword:
        qs = qs.filter(
            Q(title__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(address__icontains=keyword)
            | Q(district__icontains=keyword)
            | Q(municipality__icontains=keyword)
        )

    if location_query:
        qs = qs.filter(
            Q(title__icontains=location_query)
            | Q(address__icontains=location_query)
            | Q(district__icontains=location_query)
            | Q(municipality__icontains=location_query)
            | Q(ward_number__icontains=location_query)
            | Q(property_overview__icontains=location_query)
        )

    # Location filters
    district = request.query_params.get('district')
    if district:
        qs = qs.filter(district__icontains=district)

    municipality = request.query_params.get('municipality')
    if municipality:
        qs = qs.filter(municipality__icontains=municipality)

    province = request.query_params.get('province')
    if province:
        qs = qs.filter(province__iexact=province)

    # Ward filter
    ward_number = request.query_params.get('ward_number')
    if ward_number:
        qs = qs.filter(ward_number=ward_number)

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

    # Rating filter (use annotation since average_rating is a model property)
    min_rating = request.query_params.get('min_rating')
    if min_rating:
        qs = qs.annotate(avg_rating=Avg('reviews__rating')).filter(avg_rating__gte=float(min_rating))

    center_lat = request.query_params.get('center_lat')
    center_lng = request.query_params.get('center_lng')
    radius_km = request.query_params.get('radius_km')
    if center_lat and center_lng and radius_km:
        try:
            radius_km = float(radius_km)
            center_lat = float(center_lat)
            center_lng = float(center_lng)
            lat_delta = radius_km / 111.0
            lng_delta = radius_km / max(111.0 * abs(math.cos(math.radians(center_lat))), 0.01)
            qs = qs.filter(
                latitude__gte=center_lat - lat_delta,
                latitude__lte=center_lat + lat_delta,
                longitude__gte=center_lng - lng_delta,
                longitude__lte=center_lng + lng_delta,
            )
        except (TypeError, ValueError):
            logger.debug('Ignoring invalid radius filter values')

    # Bounding box filter for map viewport
    ne_lat = request.query_params.get('ne_lat')
    ne_lng = request.query_params.get('ne_lng')
    sw_lat = request.query_params.get('sw_lat')
    sw_lng = request.query_params.get('sw_lng')

    if all([ne_lat, ne_lng, sw_lat, sw_lng]):
        try:
            qs = qs.filter(
                latitude__gte=float(sw_lat),
                latitude__lte=float(ne_lat),
                longitude__gte=float(sw_lng),
                longitude__lte=float(ne_lng),
            )
        except (TypeError, ValueError):
            logger.debug('Ignoring invalid bounding box filter values')

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
    try:
        limit = min(int(request.query_params.get('limit', 200)), 500)
    except (TypeError, ValueError):
        limit = 200

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


@api_view(['GET'])
def location_data(request):
    """Return cascading location data for filters.

    Query params:
        province  -> returns districts in that province
        district  -> returns municipalities in that district
        municipality -> returns ward numbers in that municipality
        (none)    -> returns all provinces
    """
    available = Property.objects.filter(
        status=Property.Status.AVAILABLE, is_approved=True
    ).order_by()  # clear default ordering so .distinct() works on PostgreSQL

    province = request.query_params.get('province')
    district = request.query_params.get('district')
    municipality = request.query_params.get('municipality')

    if municipality:
        qs = available.filter(municipality__iexact=municipality)
        if district:
            qs = qs.filter(district__iexact=district)
        wards = sorted(
            qs.values_list('ward_number', flat=True).distinct(),
            key=lambda w: int(w) if w.isdigit() else 0,
        )
        return Response({'wards': wards})

    if district:
        qs = available.filter(district__iexact=district)
        municipalities = sorted(
            qs.values_list('municipality', flat=True).distinct()
        )
        return Response({'municipalities': municipalities})

    if province:
        districts = [label for label, _ in get_canonical_district_choices(province)]
        return Response({'districts': districts})

    # No filter = return all provinces
    provinces = sorted(
        available.exclude(province='').values_list('province', flat=True).distinct()
    )
    return Response({'provinces': provinces})
