from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('chat/', views.chat, name='chat'),
    path('recommendations/', views.get_recommendations, name='recommendations'),
    path('area-insights/', views.area_insights, name='area_insights'),
]
