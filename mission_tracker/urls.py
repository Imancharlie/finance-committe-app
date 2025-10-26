# If your offline_view is in tracker.views
# finance-committe-app/mission_tracker/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from tracker.views import offline_view # Assuming you put it here

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pwa.urls')),
    path('', include('tracker.urls')),
    path('offline/', offline_view, name='offline'), # Add this line
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]