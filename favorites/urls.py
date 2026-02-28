from django.urls import path

from favorites import views

app_name = "favorites"

urlpatterns = [
    path("", views.favorites_list, name="list"),
    path("toggle/<int:property_id>/", views.toggle_favorite, name="toggle"),
    path("check/<int:property_id>/", views.check_favorite, name="check"),
]
