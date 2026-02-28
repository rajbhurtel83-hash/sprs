from django.urls import path

from reviews import views

app_name = 'reviews'

urlpatterns = [
    path('add/<int:property_id>/', views.add_review, name='add'),
    path('delete/<int:pk>/', views.delete_review, name='delete'),
]
