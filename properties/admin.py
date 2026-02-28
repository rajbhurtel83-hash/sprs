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
    list_display = ('title', 'owner', 'property_type', 'district', 'municipality', 'price', 'rental_purpose', 'status', 'is_approved', 'views_count', 'created_at')
    list_filter = ('property_type', 'status', 'is_approved', 'rental_purpose', 'district', 'created_at')
    search_fields = ('title', 'description', 'address', 'district', 'municipality')
    list_editable = ('is_approved', 'status')
    readonly_fields = ('created_at', 'updated_at', 'views_count')
    filter_horizontal = ('amenities',)
    inlines = [PropertyImageInline]
    ordering = ('-created_at',)


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
