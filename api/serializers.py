from rest_framework import serializers
from properties.models import Property, PropertyImage, Amenity
from reviews.models import Review


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'icon']


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'caption', 'is_primary']


class PropertyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views and map markers."""
    primary_image = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    property_type_display = serializers.CharField(
        source='get_property_type_display', read_only=True
    )
    owner_name = serializers.SerializerMethodField()
    trust_score = serializers.IntegerField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = Property
        fields = [
            'id', 'title', 'property_type', 'property_type_display',
            'province', 'district', 'municipality', 'ward_number', 'address',
            'price', 'num_rooms', 'rental_purpose', 'latitude', 'longitude',
            'status', 'average_rating', 'review_count', 'primary_image',
            'owner_name', 'trust_score', 'is_verified', 'created_at',
        ]

    def get_primary_image(self, obj):
        img = obj.primary_image
        if img:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(img.image.url)
            return img.image.url
        return None

    def get_owner_name(self, obj):
        return obj.owner.get_full_name() or obj.owner.username


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer."""
    images = PropertyImageSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    property_type_display = serializers.CharField(
        source='get_property_type_display', read_only=True
    )
    owner_name = serializers.SerializerMethodField()
    trust_score = serializers.IntegerField(read_only=True)
    verification_badges = serializers.SerializerMethodField()
    amenity_cards = serializers.SerializerMethodField()
    overview_cards = serializers.SerializerMethodField()
    nearby_place_cards = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'title', 'property_type', 'property_type_display',
            'description', 'province', 'district', 'municipality', 'ward_number',
            'address', 'price', 'num_rooms', 'rental_purpose',
            'amenities', 'latitude', 'longitude', 'status',
            'contact_phone', 'contact_email', 'average_rating',
            'review_count', 'images', 'owner_name', 'views_count',
            'created_at', 'updated_at', 'trust_score', 'verification_badges',
            'amenity_cards', 'overview_cards', 'nearby_place_cards',
            'property_overview', 'amenity_settings', 'nearby_places',
            'house_rules', 'available_from', 'minimum_rental_duration',
            'maximum_occupants', 'furnishing_status', 'total_area', 'floor_number',
            'facing_direction', 'road_access_width', 'owner_verified',
            'government_id_verified', 'ownership_document_verified',
            'utility_bill_verified', 'phone_verified', 'email_verified',
            'location_verified', 'recently_inspected', 'verification_date',
            'is_verified', 'is_approved',
        ]

    def get_owner_name(self, obj):
        return obj.owner.get_full_name() or obj.owner.username

    def get_verification_badges(self, obj):
        return obj.verification_badges

    def get_amenity_cards(self, obj):
        return obj.amenity_cards

    def get_overview_cards(self, obj):
        return obj.overview_cards

    def get_nearby_place_cards(self, obj):
        return obj.nearby_place_cards


class MapPropertySerializer(serializers.ModelSerializer):
    """Enhanced serializer for map markers with full property details."""
    primary_image = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    property_type_display = serializers.CharField(
        source='get_property_type_display', read_only=True
    )
    rental_purpose_display = serializers.CharField(
        source='get_rental_purpose_display', read_only=True
    )
    owner_name = serializers.SerializerMethodField()
    amenities = AmenitySerializer(many=True, read_only=True)
    short_description = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    trust_score = serializers.IntegerField(read_only=True)
    verification_badges = serializers.SerializerMethodField()
    amenity_cards = serializers.SerializerMethodField()
    nearby_place_cards = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'title', 'property_type', 'property_type_display',
            'province', 'district', 'municipality', 'ward_number', 'address',
            'price', 'latitude', 'longitude', 'num_rooms',
            'average_rating', 'review_count', 'primary_image',
            'rental_purpose', 'rental_purpose_display', 'owner_name',
            'amenities', 'short_description', 'url', 'status',
            'contact_phone', 'contact_email', 'description', 'trust_score',
            'verification_badges', 'amenity_cards', 'nearby_place_cards',
            'distance_km', 'is_verified',
        ]

    def get_primary_image(self, obj):
        img = obj.primary_image
        if img:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(img.image.url)
            return img.image.url
        return None

    def get_average_rating(self, obj):
        return obj.average_rating or 0

    def get_review_count(self, obj):
        return obj.review_count or 0

    def get_owner_name(self, obj):
        return obj.owner.get_full_name() or obj.owner.username

    def get_short_description(self, obj):
        if obj.description:
            return obj.description[:150] + '...' if len(obj.description) > 150 else obj.description
        return ''

    def get_url(self, obj):
        return f'/properties/{obj.id}/'

    def get_verification_badges(self, obj):
        return obj.verification_badges

    def get_amenity_cards(self, obj):
        return obj.amenity_cards

    def get_nearby_place_cards(self, obj):
        return obj.nearby_place_cards

    def get_distance_km(self, obj):
        request = self.context.get('request')
        if not request:
            return None

        center_lat = request.query_params.get('center_lat')
        center_lng = request.query_params.get('center_lng')
        if not center_lat or not center_lng or not obj.latitude or not obj.longitude:
            return None

        from math import atan2, cos, radians, sin, sqrt

        lat1 = radians(float(center_lat))
        lon1 = radians(float(center_lng))
        lat2 = radians(float(obj.latitude))
        lon2 = radians(float(obj.longitude))

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return round(6371 * c, 2)
