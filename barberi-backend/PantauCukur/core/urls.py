# C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\urls.py
from django.urls import path
from . import views

urlpatterns = [
    # === SESSION MANAGEMENT ===
    path('session/start/', views.start_session, name='start_session'),
    path('session/end/', views.end_session, name='end_session'),
    path('session/update/', views.update_session, name='update_session'),
    path('session/heartbeat/', views.heartbeat, name='heartbeat'),
    
    # === SESSION DATA ===
    path('session/summary/', views.get_sessions_summary, name='get_sessions_summary'),
    # path('session/<int:session_id>/detail/', views.get_session_detail, name='get_session_detail'),  # ❌ TIDAK ADA
    # path('session/metrics/', views.get_session_metrics, name='get_session_metrics'),  # ❌ TIDAK ADA
    
    # === CAMERA & ROI ===
    path('camera/frame/', views.get_camera_frame, name='get_camera_frame'),
    path('roi/update/', views.update_roi, name='update_roi'),
    path('session/<int:session_id>/timeline/', views.get_session_timeline, name='get_session_timeline'),
]