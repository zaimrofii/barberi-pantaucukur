from django.urls import path
from . import views

urlpatterns = [
    path('session/start/', views.start_session, name='start_session'),
    path('session/end/', views.end_session, name='end_session'),
    path('session/summary/', views.get_sessions_summary, name='get_all_sessions'),
]