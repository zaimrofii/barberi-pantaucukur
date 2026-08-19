# C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\admin.py
from django.contrib import admin
from .models import BarberSession

@admin.register(BarberSession)
class BarberSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'chair_number', 'session_status', 'confidence_score', 'is_valid', 'start_time']
    list_filter = ['session_status', 'is_valid', 'chair_number']
    search_fields = ['id', 'chair_number']  # ← buat debugging
    ordering = ['-start_time']  # ← urutkan terbaru di atas