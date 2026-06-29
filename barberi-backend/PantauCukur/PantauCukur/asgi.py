# BARBERI/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from core.consumers import ChatConsumer 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PantauCukur.settings')

application = ProtocolTypeRouter({
    # Jalur HTTP Biasa
    "http": get_asgi_application(),
    
    # Jalur WebSocket (Real-time update PantauCukur)
    "websocket": URLRouter([
        # GUNAKAN .as_asgi() untuk Consumer
        path("ws/test/", ChatConsumer.as_asgi()),
    ]),
})