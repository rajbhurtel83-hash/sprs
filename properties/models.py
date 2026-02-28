from django.db import models
from django.conf import settings
from django.urls import reverse
from django.db.models import Avg

_property = property  # save built-in


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
    district = models.CharField(max_length=100)
    municipality = models.CharField(max_length=100, blank=True)
    ward_number = models.CharField(max_length=10)
    address = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    num_rooms = models.PositiveIntegerField(default=1)
    rental_purpose = models.CharField(
        max_length=20,
        choices=RentalPurpose.choices,
        default=RentalPurpose.ANY,
    )
    amenities = models.ManyToManyField(Amenity, blank=True, related_name='properties')
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
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    is_approved = models.BooleanField(default=True)
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
