from django.contrib import admin
from django.urls import path, include # Tambahkan 'include' di sini

urlpatterns = [
    path('admin/', admin.site.urls),
    # Pastikan nama app kamu adalah 'core' atau sesuaikan dengan nama app-mu
    path('api/', include('core.urls')), 
]