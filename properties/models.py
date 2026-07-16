from functools import lru_cache

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.db.models import Avg
from django.utils import timezone
from datetime import datetime

from users.management.commands.nepal_data import DISTRICTS

_property = property  # save built-in


@lru_cache(maxsize=1)
def get_canonical_district_choices(province=None):
    """Return canonical Nepal district choices, optionally filtered by province."""
    choices = []
    seen = set()
    province_filter = province.strip().lower() if isinstance(province, str) and province.strip() else None

    for district in DISTRICTS:
        if province_filter and district["province"].strip().lower() != province_filter:
            continue

        name = district["name"].strip()
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        choices.append((name, name))

    return tuple(choices)


def normalize_nepal_district(value):
    """Normalize district names to the canonical Nepal district spelling."""
    if not isinstance(value, str):
        return value

    cleaned = value.strip()
    if not cleaned:
        return cleaned

    lookup = {label.lower(): label for label, _ in get_canonical_district_choices()}
    return lookup.get(cleaned.lower(), cleaned)


class Amenity(models.Model):
    """Amenity that a property can offer."""
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default='bi-check-circle')

    class Meta:
        verbose_name_plural = 'Amenities'
        ordering = ['name']

    def __str__(self):
        return self.name


class Property(models.Model):
    """Model representing a rental property listing."""

    class AmenityStatus(models.TextChoices):
        INCLUDED = 'included', 'Included in Rent'
        EXTRA = 'extra', 'Extra Monthly Charge'
        USAGE = 'usage', 'Pay As You Use'
        UNAVAILABLE = 'unavailable', 'Not Available'

    class FurnishingStatus(models.TextChoices):
        FURNISHED = 'furnished', 'Furnished'
        SEMI_FURNISHED = 'semi_furnished', 'Semi Furnished'
        UNFURNISHED = 'unfurnished', 'Unfurnished'

    class PropertyType(models.TextChoices):
        ROOM = 'room', 'Room'
        FLAT = 'flat', 'Flat'
        APARTMENT = 'apartment', 'Apartment'
        HOUSE = 'house', 'House'
        LAND = 'land', 'Land'
        COMMERCIAL = 'commercial', 'Commercial Space'

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        RENTED = 'rented', 'Rented'
        UNAVAILABLE = 'unavailable', 'Unavailable'

    class RentalPurpose(models.TextChoices):
        FAMILY = 'family', 'Family'
        OFFICE = 'office', 'Office'
        STUDENT = 'student', 'Student'
        ANY = 'any', 'Any'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='properties',
    )
    title = models.CharField(max_length=200)
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.ROOM,
    )
    description = models.TextField()
    province = models.CharField(max_length=50, blank=True, db_index=True)
    district = models.CharField(max_length=100)
    municipality = models.CharField(max_length=100, blank=True)
    ward_number = models.CharField(max_length=10)
    address = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    num_rooms = models.PositiveIntegerField(default=1)
    rental_purpose = models.CharField(
        max_length=20,
        choices=RentalPurpose.choices,
        default=RentalPurpose.ANY,
    )
    amenities = models.ManyToManyField(Amenity, blank=True, related_name='properties')
    amenity_settings = models.JSONField(default=dict, blank=True)
    property_overview = models.JSONField(default=dict, blank=True)
    nearby_places = models.JSONField(default=list, blank=True)
    house_rules = models.TextField(blank=True)
    total_area = models.CharField(max_length=100, blank=True)
    floor_number = models.CharField(max_length=50, blank=True)
    facing_direction = models.CharField(max_length=50, blank=True)
    road_access_width = models.CharField(max_length=50, blank=True)
    furnishing_status = models.CharField(
        max_length=20,
        choices=FurnishingStatus.choices,
        default=FurnishingStatus.UNFURNISHED,
        blank=True,
    )
    available_from = models.DateField(null=True, blank=True)
    minimum_rental_duration = models.PositiveSmallIntegerField(null=True, blank=True)
    maximum_occupants = models.PositiveSmallIntegerField(null=True, blank=True)
    owner_citizenship = models.FileField(upload_to='verification/%Y/%m/', blank=True, null=True)
    ownership_certificate = models.FileField(upload_to='verification/%Y/%m/', blank=True, null=True)
    land_tax_receipt = models.FileField(upload_to='verification/%Y/%m/', blank=True, null=True)
    utility_bill = models.FileField(upload_to='verification/%Y/%m/', blank=True, null=True)
    live_selfie = models.ImageField(upload_to='verification/%Y/%m/', blank=True, null=True)
    owner_verified = models.BooleanField(default=False)
    government_id_verified = models.BooleanField(default=False)
    ownership_document_verified = models.BooleanField(default=False)
    utility_bill_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    location_verified = models.BooleanField(default=False)
    recently_inspected = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r'^\d{10}$', 'Contact phone must be exactly 10 digits.')],
    )
    contact_email = models.EmailField(blank=True)
    is_approved = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Properties'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['district']),
            models.Index(fields=['municipality']),
            models.Index(fields=['property_type']),
            models.Index(fields=['price']),
            models.Index(fields=['status']),
            models.Index(fields=['rental_purpose']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.district = normalize_nepal_district(self.district)
        if isinstance(self.province, str):
            self.province = self.province.strip()
        if isinstance(self.municipality, str):
            self.municipality = self.municipality.strip()
        if isinstance(self.address, str):
            self.address = self.address.strip()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        errors = {}

        if self.price is not None and self.price < 0:
            errors['price'] = 'Price cannot be negative.'

        if self.contact_phone:
            contact_phone = self.contact_phone.strip()
            if not contact_phone.isdigit() or len(contact_phone) != 10:
                errors['contact_phone'] = 'Contact phone must be exactly 10 digits.'
            else:
                self.contact_phone = contact_phone

        if self.contact_email:
            contact_email = self.contact_email.strip()
            try:
                from django.core.validators import validate_email
                validate_email(contact_email)
            except ValidationError:
                errors['contact_email'] = 'Enter a valid email address.'
            else:
                self.contact_email = contact_email.lower()

        if errors:
            raise ValidationError(errors)

    def get_absolute_url(self):
        return reverse('properties:detail', kwargs={'pk': self.pk})

    @_property
    def primary_image(self):
        """Return the first image or None."""
        return self.images.first()

    @_property
    def average_rating(self):
        """Return the average rating for this property."""
        avg = self.reviews.aggregate(avg=Avg('rating'))['avg']
        return round(avg, 1) if avg else 0

    @_property
    def review_count(self):
        return self.reviews.count()

    @_property
    def has_location(self):
        return self.latitude is not None and self.longitude is not None

    @_property
    def amenity_list(self):
        return list(self.amenities.values_list('name', flat=True))

    @_property
    def amenity_cards(self):
        cards = []
        amenity_settings = self.amenity_settings or {}
        badge_classes = {
            self.AmenityStatus.INCLUDED: 'bg-success',
            self.AmenityStatus.EXTRA: 'bg-warning text-dark',
            self.AmenityStatus.USAGE: 'bg-info text-dark',
            self.AmenityStatus.UNAVAILABLE: 'bg-secondary',
        }

        for amenity in self.amenities.all():
            config = amenity_settings.get(str(amenity.pk), amenity_settings.get(amenity.name, {}))
            status = config.get('status') or self.AmenityStatus.INCLUDED
            monthly_charge = config.get('monthly_charge') or config.get('charge')
            cards.append({
                'name': amenity.name,
                'icon': amenity.icon,
                'status': status,
                'status_label': dict(self.AmenityStatus.choices).get(status, status.title()),
                'badge_class': badge_classes.get(status, 'bg-secondary'),
                'monthly_charge': monthly_charge,
                'notes': config.get('notes', ''),
            })

        return cards

    @_property
    def verification_badges(self):
        verification_date = self.verification_date or self._verification_date_from_metadata()
        badges = [
            {'label': 'Verified Owner', 'active': self.owner_verified, 'icon': 'bi-shield-check'},
            {'label': 'Verified Property', 'active': self.is_verified, 'icon': 'bi-patch-check'},
            {'label': 'Government ID Verified', 'active': self.government_id_verified or bool(self.owner_citizenship), 'icon': 'bi-person-badge'},
            {'label': 'Ownership Document Verified', 'active': self.ownership_document_verified or bool(self.ownership_certificate), 'icon': 'bi-file-earmark-check'},
            {'label': 'Utility Bill Verified', 'active': self.utility_bill_verified or bool(self.utility_bill), 'icon': 'bi-receipt'},
            {'label': 'Google Maps Location Verified', 'active': self.location_verified or self.has_location, 'icon': 'bi-geo-alt-fill'},
            {'label': 'Phone Number Verified', 'active': self.phone_verified or bool(self.contact_phone), 'icon': 'bi-telephone-check'},
            {'label': 'Email Verified', 'active': self.email_verified or bool(self.contact_email), 'icon': 'bi-envelope-check'},
            {'label': 'Recently Inspected', 'active': self.recently_inspected, 'icon': 'bi-eye'},
        ]

        if verification_date:
            badges.append({
                'label': 'Verification Date',
                'active': True,
                'icon': 'bi-calendar-check',
                'detail': verification_date.strftime('%b %d, %Y'),
            })

        return badges

    @_property
    def overview_cards(self):
        overview = self.property_overview or {}

        def value_or_default(value, default='N/A'):
            if value in (None, '', []):
                return default
            if isinstance(value, bool):
                return 'Yes' if value else 'No'
            if hasattr(value, 'strftime'):
                return value.strftime('%b %d, %Y')
            return value

        cards = [
            ('Property Type', self.get_property_type_display(), 'bi-building'),
            ('Total Area', value_or_default(overview.get('total_area') or self.total_area), 'bi-aspect-ratio'),
            ('Floor Number', value_or_default(overview.get('floor_number') or self.floor_number), 'bi-layers'),
            ('Facing Direction', value_or_default(overview.get('facing_direction') or self.facing_direction), 'bi-compass'),
            ('Road Access Width', value_or_default(overview.get('road_access_width') or self.road_access_width), 'bi-signpost-split'),
            ('Furnishing', self.get_furnishing_status_display(), 'bi-house-check'),
            ('Balcony', value_or_default(overview.get('balcony'), 'No'), 'bi-window'),
            ('Natural Lighting', value_or_default(overview.get('natural_lighting'), 'N/A'), 'bi-brightness-high'),
            ('Ventilation', value_or_default(overview.get('ventilation'), 'N/A'), 'bi-wind'),
            ('Pet Friendly', value_or_default(overview.get('pet_friendly'), 'No'), 'bi-heart'),
            ('Smoking Allowed', value_or_default(overview.get('smoking_allowed'), 'No'), 'bi-patch-exclamation'),
            ('Family Preferred', value_or_default(overview.get('family_preferred'), 'Yes'), 'bi-people'),
            ('Students Allowed', value_or_default(overview.get('students_allowed'), 'Yes'), 'bi-mortarboard'),
            ('Office Allowed', value_or_default(overview.get('office_allowed'), 'No'), 'bi-briefcase'),
            ('Bachelor Allowed', value_or_default(overview.get('bachelor_allowed'), 'Yes'), 'bi-person-badge'),
            ('Available From', value_or_default(overview.get('available_from') or self.available_from), 'bi-calendar3'),
            ('Minimum Rental Duration', value_or_default(overview.get('minimum_rental_duration') or self.minimum_rental_duration, 'N/A'), 'bi-hourglass-split'),
            ('Maximum Occupants', value_or_default(overview.get('maximum_occupants') or self.maximum_occupants, 'N/A'), 'bi-people-fill'),
            ('Nearby Landmarks', value_or_default(overview.get('nearby_landmarks')), 'bi-geo'),
            ('Public Transport Distance', value_or_default(overview.get('public_transport_distance')), 'bi-bus-front'),
            ('School Distance', value_or_default(overview.get('school_distance')), 'bi-backpack2'),
            ('Hospital Distance', value_or_default(overview.get('hospital_distance')), 'bi-heart-pulse'),
            ('Market Distance', value_or_default(overview.get('market_distance')), 'bi-shop'),
            ('Temple Distance', value_or_default(overview.get('temple_distance')), 'bi-flower1'),
            ('Parking Capacity', value_or_default(overview.get('parking_capacity')), 'bi-p-square'),
            ('Water Supply Hours', value_or_default(overview.get('water_supply_hours')), 'bi-droplet-half'),
            ('Internet Providers Available', value_or_default(overview.get('internet_providers_available')), 'bi-wifi'),
            ('Electric Backup', value_or_default(overview.get('electric_backup')), 'bi-battery-charging'),
            ('CCTV Availability', value_or_default(overview.get('cctv_availability'), 'No'), 'bi-camera-video'),
            ('Lift Availability', value_or_default(overview.get('lift_availability'), 'No'), 'bi-arrow-up-circle'),
            ('Security Guard', value_or_default(overview.get('security_guard'), 'No'), 'bi-shield-lock'),
            ('Waste Collection', value_or_default(overview.get('waste_collection'), 'No'), 'bi-trash3'),
            ('Noise Level', value_or_default(overview.get('noise_level')), 'bi-volume-down'),
            ('Neighborhood Description', value_or_default(overview.get('neighborhood_description')), 'bi-shop-window'),
            ('House Rules', value_or_default(overview.get('house_rules') or self.house_rules), 'bi-journal-text'),
        ]

        return [
            {
                'label': label,
                'value': value,
                'icon': icon,
            }
            for label, value, icon in cards
        ]

    @_property
    def nearby_place_cards(self):
        places = self.nearby_places or []
        normalized = []

        for place in places:
            if isinstance(place, str):
                normalized.append({'name': place, 'distance': ''})
                continue
            if isinstance(place, dict):
                normalized.append({
                    'name': place.get('name') or place.get('type') or 'Nearby Place',
                    'distance': place.get('distance') or place.get('distance_label') or '',
                    'type': place.get('type') or place.get('category') or '',
                    'icon': place.get('icon') or 'bi-geo-alt',
                })

        return normalized

    @_property
    def trust_score(self):
        score = 0
        score += 15 if self.owner_verified else 5 if self.owner else 0
        score += 15 if self.is_verified else 8 if self.is_approved else 0
        score += 10 if self.government_id_verified or self.owner_citizenship else 0
        score += 10 if self.ownership_document_verified or self.ownership_certificate else 0
        score += 8 if self.utility_bill_verified or self.utility_bill else 0
        score += 8 if self.location_verified or self.has_location else 0
        score += 5 if self.phone_verified or self.contact_phone else 0
        score += 5 if self.email_verified or self.contact_email else 0
        score += min(len(self.images.all()) * 2, 10)
        score += min(self.review_count * 2, 10)

        completeness = 0
        for field_name in ['title', 'description', 'district', 'municipality', 'address', 'price']:
            if getattr(self, field_name):
                completeness += 1
        completeness += 1 if self.property_overview else 0
        completeness += 1 if self.nearby_places else 0
        score += min(completeness * 2, 10)

        if self.verification_date:
            days_since = (timezone.now() - self.verification_date).days
            score += 5 if days_since <= 365 else 2
        elif self.recently_inspected:
            score += 5

        return min(score, 100)

    def _verification_date_from_metadata(self):
        metadata_date = (self.property_overview or {}).get('verification_date')
        if not metadata_date:
            return None
        try:
            return datetime.fromisoformat(metadata_date)
        except (TypeError, ValueError):
            return None


class PropertyImage(models.Model):
    """Model for property images."""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.ImageField(upload_to='properties/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'uploaded_at']

    def __str__(self):
        return f"Image for {self.property.title}"


class PropertyRequest(models.Model):
    """Request for property visit, rental inquiry, or booking."""

    class RequestType(models.TextChoices):
        VISIT = 'visit', 'Property Visit'
        INQUIRY = 'inquiry', 'Rental Inquiry'
        BOOKING = 'booking', 'Booking Request'

    class RequestStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='requests',
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='property_requests',
    )
    request_type = models.CharField(
        max_length=20,
        choices=RequestType.choices,
        default=RequestType.VISIT,
    )
    message = models.TextField()
    visit_date = models.DateField(null=True, blank=True, help_text='Preferred visit date (for visit requests)')
    visit_time = models.TimeField(null=True, blank=True, help_text='Preferred visit time (for visit requests)')
    # Booking-specific fields
    move_in_date = models.DateField(null=True, blank=True, help_text='Preferred move-in date (for bookings)')
    duration_months = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Rental duration in months')
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_request_type_display()} for {self.property.title} by {self.requester.username}"
