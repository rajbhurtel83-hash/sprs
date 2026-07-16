from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('property', 'reviewer', 'rating', 'cleanliness', 'location', 'security', 'created_at')
    list_filter = ('rating', 'cleanliness', 'location', 'security', 'created_at')
    search_fields = ('property__title', 'reviewer__username', 'comment')
    readonly_fields = ('created_at', 'updated_at')
