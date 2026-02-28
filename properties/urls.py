from django.urls import path
from . import views

app_name = 'properties'

urlpatterns = [
    path('', views.property_list, name='list'),
    path('map/', views.map_explorer, name='map_explorer'),
    path('map/legacy/', views.map_explorer_legacy, name='map_explorer_legacy'),
    path('compare/', views.property_compare, name='compare'),
    path('compare/add/<int:pk>/', views.add_to_comparison, name='add_to_comparison'),
    path('compare/remove/<int:pk>/', views.remove_from_comparison, name='remove_from_comparison'),
    path('compare/clear/', views.clear_comparison, name='clear_comparison'),
    path('create/', views.property_create, name='create'),
    path('my/', views.my_properties, name='my_properties'),
    path('requests/', views.manage_requests, name='manage_requests'),
    path('requests/<int:pk>/respond/', views.respond_request, name='respond_request'),
    path('<int:pk>/', views.property_detail, name='detail'),
    path('<int:pk>/edit/', views.property_edit, name='edit'),
    path('<int:pk>/delete/', views.property_delete, name='delete'),
    path('<int:pk>/request/', views.submit_request, name='submit_request'),
    path('image/<int:pk>/delete/', views.property_image_delete, name='image_delete'),
]
