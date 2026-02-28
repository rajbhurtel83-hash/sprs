from django.urls import path
from . import views

app_name = 'adminpanel'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('users/', views.manage_users, name='manage_users'),
    path('users/<int:pk>/toggle/', views.toggle_user_active, name='toggle_user'),
    path('properties/', views.manage_properties, name='manage_properties'),
    path('properties/<int:pk>/toggle-approval/', views.toggle_property_approval, name='toggle_approval'),
    path('properties/<int:pk>/delete/', views.delete_property, name='delete_property'),
]
