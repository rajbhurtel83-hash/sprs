from django.contrib import admin
from .models import Property, PropertyImage, Amenity, PropertyRequest


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'property_type', 'district', 'municipality', 'price', 'rental_purpose', 'status', 'is_approved', 'is_verified', 'owner_verified', 'trust_score_display', 'views_count', 'created_at')
    list_filter = ('property_type', 'status', 'is_approved', 'is_verified', 'owner_verified', 'rental_purpose', 'district', 'created_at')
    search_fields = ('title', 'description', 'address', 'district', 'municipality')
    list_editable = ('is_approved', 'status', 'is_verified')
    readonly_fields = ('created_at', 'updated_at', 'views_count', 'trust_score_display')
    filter_horizontal = ('amenities',)
    inlines = [PropertyImageInline]
    ordering = ('-created_at',)

    fieldsets = (
        ('Core Details', {
            'fields': ('owner', 'title', 'property_type', 'status', 'rental_purpose', 'price', 'description')
        }),
        ('Location', {
            'fields': ('province', 'district', 'municipality', 'ward_number', 'address', 'latitude', 'longitude')
        }),
        ('Property Intelligence', {
            'fields': ('total_area', 'floor_number', 'facing_direction', 'road_access_width', 'furnishing_status', 'available_from', 'minimum_rental_duration', 'maximum_occupants', 'house_rules', 'property_overview', 'amenity_settings', 'nearby_places')
        }),
        ('Verification', {
            'fields': ('owner_citizenship', 'ownership_certificate', 'land_tax_receipt', 'utility_bill', 'live_selfie', 'owner_verified', 'government_id_verified', 'ownership_document_verified', 'utility_bill_verified', 'phone_verified', 'email_verified', 'location_verified', 'recently_inspected', 'verification_date', 'is_verified', 'is_approved')
        }),
        ('Contact & Metrics', {
            'fields': ('contact_phone', 'contact_email', 'views_count', 'created_at', 'updated_at')
        }),
    )

    def trust_score_display(self, obj):
        return f"{obj.trust_score}/100"

    trust_score_display.short_description = 'Trust Score'


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property', 'caption', 'is_primary', 'uploaded_at')
    list_filter = ('is_primary', 'uploaded_at')


@admin.register(PropertyRequest)
class PropertyRequestAdmin(admin.ModelAdmin):
    list_display = ('property', 'requester', 'request_type', 'status', 'created_at', 'responded_at')
    list_filter = ('request_type', 'status', 'created_at')
    search_fields = ('property__title', 'requester__username', 'message')
    readonly_fields = ('created_at',)
