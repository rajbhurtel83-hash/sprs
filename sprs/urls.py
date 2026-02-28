from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_view, name='home'),
    path('users/', include('users.urls')),
    path('properties/', include('properties.urls')),
    path('messaging/', include('messaging.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('panel/', include('adminpanel.urls')),
    path('favorites/', include('favorites.urls')),
    path('reviews/', include('reviews.urls')),
    path('notifications/', include('notifications.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('api/v1/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler404 = 'sprs.views.custom_404'
handler500 = 'sprs.views.custom_500'
