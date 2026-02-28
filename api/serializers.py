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

    class Meta:
        model = Property
        fields = [
            'id', 'title', 'property_type', 'property_type_display',
            'district', 'municipality', 'ward_number', 'address',
            'price', 'num_rooms', 'rental_purpose', 'latitude', 'longitude',
            'status', 'average_rating', 'review_count', 'primary_image',
            'owner_name', 'created_at',
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

    class Meta:
        model = Property
        fields = [
            'id', 'title', 'property_type', 'property_type_display',
            'description', 'district', 'municipality', 'ward_number',
            'address', 'price', 'num_rooms', 'rental_purpose',
            'amenities', 'latitude', 'longitude', 'status',
            'contact_phone', 'contact_email', 'average_rating',
            'review_count', 'images', 'owner_name', 'views_count',
            'created_at', 'updated_at',
        ]

    def get_owner_name(self, obj):
        return obj.owner.get_full_name() or obj.owner.username


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

    class Meta:
        model = Property
        fields = [
            'id', 'title', 'property_type', 'property_type_display',
            'district', 'municipality', 'ward_number', 'address',
            'price', 'latitude', 'longitude', 'num_rooms',
            'average_rating', 'review_count', 'primary_image',
            'rental_purpose', 'rental_purpose_display', 'owner_name',
            'amenities', 'short_description', 'url', 'status',
            'contact_phone', 'contact_email', 'description',
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
