from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('properties/', views.PropertyListAPIView.as_view(), name='property_list'),
    path('properties/map/', views.map_properties, name='map_properties'),
    path('properties/<int:pk>/', views.PropertyDetailAPIView.as_view(), name='property_detail'),
    path('amenities/', views.amenities_list, name='amenities'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
]
