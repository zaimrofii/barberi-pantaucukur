### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\admin.py`
```python
from django.contrib import admin
from .models import BarberSession

@admin.register(BarberSession)
class BarberSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'chair_number', 'session_status', 'confidence_score', 'is_valid', 'start_time']
    list_filter = ['session_status', 'is_valid', 'chair_number']
    search_fields = ['id', 'chair_number']
    ordering = ['-start_time']
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\apps.py`
```python
from django.apps import AppConfig

class CoreConfig(AppConfig):
    name = 'core'
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\consumers.py`
```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .views import get_current_summary_data

class ChatConsumer(AsyncWebsocketConsumer):
    """[CLASS STATE / ATTRS]: room_group_name"""

    async def connect(self):
        """[SIDE EFFECTS]: self.channel_layer.group_add, self.send"""
        pass

    async def disconnect(self, close_code):
        """[INPUT PARAMS]: close_code
[SIDE EFFECTS]: self.channel_layer.group_discard"""
        pass

    @database_sync_to_async
    def get_summary_from_db(self):
        pass

    async def send_status_update(self, event):
        """Dipanggil saat ada event dari layer group.
Kamera kirim status -> Backend simpan DB -> Backend trigger group_send -> Fungsi ini jalan.
----------------------------------------
[INPUT PARAMS]: event
[SIDE EFFECTS]: self.send"""
        pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\models.py`
```python
from django.db import models

class BarberSession(models.Model):
    chair_number = models.IntegerField()
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    is_valid = models.BooleanField(default=False)
    confidence_score = models.IntegerField(default=0, help_text='Session confidence score (0-100)')
    tracking_data = models.JSONField(default=dict, help_text='Per-frame tracking metrics and session data')
    session_status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('ACTIVE', 'Active'), ('ENDED', 'Ended')], default='PENDING', help_text='State machine status')
    last_heartbeat = models.DateTimeField(null=True, blank=True, help_text='Timestamp of last heartbeat from AI Engine')
    timeout_reason = models.CharField(max_length=50, null=True, blank=True, help_text='Reason for session timeout (e.g., AI_CRASH, NETWORK_LOSS)')
    ended_by = models.CharField(max_length=20, choices=[('AI', 'AI Engine'), ('TIMEOUT', 'Timeout'), ('MANUAL', 'Manual')], default='AI', help_text='How the session was ended')

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\urls.py`
```python
from django.urls import path
from . import views
urlpatterns = [path('session/start/', views.start_session, name='start_session'), path('session/end/', views.end_session, name='end_session'), path('session/update/', views.update_session, name='update_session'), path('session/heartbeat/', views.heartbeat, name='heartbeat'), path('session/summary/', views.get_sessions_summary, name='get_sessions_summary'), path('camera/frame/', views.get_camera_frame, name='get_camera_frame'), path('roi/update/', views.update_roi, name='update_roi'), path('session/<int:session_id>/timeline/', views.get_session_timeline, name='get_session_timeline')]
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\views.py`
```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import BarberSession
import json
import base64
import redis
from .services.utils import load_config, save_config
REDIS_CLIENT = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)

@csrf_exempt
def start_session(request):
    """[HTTP PAYLOAD IN]: breakdown, chair_id, confidence_score, session_status
[HTTP RESPONSE KEYS]: message, session_id, status
[DB OPS]: BarberSession.objects.create
[SIDE EFFECTS]: get_channel_layer"""
    pass

@csrf_exempt
def end_session(request):
    """[HTTP PAYLOAD IN]: chair_id, confidence_score, session_status, timeout_reason
[HTTP RESPONSE KEYS]: confidence_score, duration, is_valid, message, session_status, status
[DB OPS]: BarberSession.objects.filter, session.save
[SIDE EFFECTS]: get_channel_layer"""
    pass

@csrf_exempt
def update_session(request):
    """Endpoint untuk update sesi dari state machine (PENDING, ACTIVE, ENDING)
----------------------------------------
[HTTP PAYLOAD IN]: breakdown, chair_id, confidence_score, is_active, session_status, timeout_reason, trigger_reason
[HTTP RESPONSE KEYS]: message, session_id, status
[DB OPS]: BarberSession.objects.create, BarberSession.objects.filter, session.save
[SIDE EFFECTS]: get_channel_layer"""
    pass

@csrf_exempt
def heartbeat(request):
    """Endpoint untuk heartbeat dari AI Engine
----------------------------------------
[HTTP PAYLOAD IN]: chair_id, confidence_score, is_active, session_status
[HTTP RESPONSE KEYS]: message, status
[DB OPS]: BarberSession.objects.filter, session.save"""
    pass

def get_current_summary_data():
    """Fungsi pembantu untuk mengambil summary yang konsisten
----------------------------------------
[RETURN SHAPES DETECTED]: Dict{ summary, valid_list, invalid_list }
[DB OPS]: BarberSession.objects.all"""
    pass

def serialize_session(s):
    """[INPUT PARAMS]: s
[RETURN SHAPES DETECTED]: Dict{ id, chair, start, duration, status, confidence_score, session_status }"""
    pass

def get_sessions_summary(request):
    """[INPUT PARAMS]: request"""
    pass

@csrf_exempt
def get_camera_frame(request):
    """[HTTP PAYLOAD IN]: rois
[HTTP RESPONSE KEYS]: message, status
[SIDE EFFECTS]: load_config"""
    pass

@csrf_exempt
def update_roi(request):
    """[HTTP PAYLOAD IN]: rois
[HTTP RESPONSE KEYS]: message, status
[SIDE EFFECTS]: save_config"""
    pass

def get_session_timeline(request, session_id):
    """[HTTP PAYLOAD IN]: transitions
[HTTP RESPONSE KEYS]: session_id, timeline
[DB OPS]: BarberSession.objects.get"""
    pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\__init__.py`
```python

```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\migrations\0001_initial.py`
```python
import django.utils.timezone
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.CreateModel(name='BarberSession', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('chair_number', models.IntegerField()), ('start_time', models.DateTimeField(default=django.utils.timezone.now)), ('end_time', models.DateTimeField(blank=True, null=True)), ('duration_seconds', models.IntegerField(default=0)), ('is_valid', models.BooleanField(default=False))], options={'ordering': ['-start_time']})]
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\migrations\0002_alter_barbersession_id.py`
```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]
    operations = [migrations.AlterField(model_name='barbersession', name='id', field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'))]
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\migrations\0003_barbersession_confidence_score_and_more.py`
```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('core', '0002_alter_barbersession_id')]
    operations = [migrations.AddField(model_name='barbersession', name='confidence_score', field=models.IntegerField(default=0, help_text='Session confidence score (0-100)')), migrations.AddField(model_name='barbersession', name='session_status', field=models.CharField(choices=[('PENDING', 'Pending'), ('ACTIVE', 'Active'), ('ENDED', 'Ended')], default='PENDING', help_text='State machine status', max_length=20)), migrations.AddField(model_name='barbersession', name='tracking_data', field=models.JSONField(default=dict, help_text='Per-frame tracking metrics and session data')), migrations.AlterField(model_name='barbersession', name='start_time', field=models.DateTimeField(auto_now_add=True))]
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\migrations\0004_barbersession_ended_by_barbersession_last_heartbeat_and_more.py`
```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('core', '0003_barbersession_confidence_score_and_more')]
    operations = [migrations.AddField(model_name='barbersession', name='ended_by', field=models.CharField(choices=[('AI', 'AI Engine'), ('TIMEOUT', 'Timeout'), ('MANUAL', 'Manual')], default='AI', help_text='How the session was ended', max_length=20)), migrations.AddField(model_name='barbersession', name='last_heartbeat', field=models.DateTimeField(blank=True, help_text='Timestamp of last heartbeat from AI Engine', null=True)), migrations.AddField(model_name='barbersession', name='timeout_reason', field=models.CharField(blank=True, help_text='Reason for session timeout (e.g., AI_CRASH, NETWORK_LOSS)', max_length=50, null=True))]
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\migrations\__init__.py`
```python

```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\detector.py`
```python
import cv2
import os
import numpy as np
import time
from ultralytics import YOLO
from dotenv import load_dotenv
from state_machine import StateMachine
from scoring_engine import ScoringEngine
from posture_classifier import PostureClassifier
from hand_activity import calculate_hand_activity
from track_manager import TrackManager
from roi_manager import ROIManager
from utils import match_keypoints_to_tracked
from logger import smart_logger

class SimpleByteTrack:
    """Simple tracker replacement for ByteTrack
----------------------------------------
[CLASS STATE / ATTRS]: frame_rate, match_thresh, max_age, min_hits, next_id, track_thresh, tracks"""

    def __init__(self, track_thresh=0.5, match_thresh=0.8, frame_rate=30):
        """[INPUT PARAMS]: track_thresh, match_thresh, frame_rate"""
        pass

    def update(self, boxes):
        """[INPUT PARAMS]: boxes"""
        pass

    def _calculate_iou(self, box1, box2):
        """[INPUT PARAMS]: box1, box2
[RETURN SHAPES DETECTED]: Literal:float"""
        pass

class TrackObject:
    """Mock BoxMot track object
----------------------------------------
[CLASS STATE / ATTRS]: age, confidence, track_id, xyxy"""

    def __init__(self, track_data):
        """[INPUT PARAMS]: track_data"""
        pass

class BarberDetector:
    """[CLASS STATE / ATTRS]: conf_threshold, frame_count, model, posture_classifier, roi_manager, rois, scoring_engine, state_machine, track_manager, tracker, use_scoring"""

    def __init__(self, model_path='yolov8n-pose.pt', rois=None):
        """[INPUT PARAMS]: model_path, rois"""
        pass

    def update_rois(self, new_rois):
        """[INPUT PARAMS]: new_rois"""
        pass

    def process_ai(self, frame):
        """Memproses frame dengan deteksi AI, pelacakan, estimasi pose, dan penilaian.

Returns:
    tuple: (stable_status, person_boxes, session_data) jika USE_SCORING=True
        (stable_status, person_boxes) jika USE_SCORING=False
----------------------------------------
[INPUT PARAMS]: frame
[RETURN SHAPES DETECTED]: Tuple(stable_status, person_boxes, Dict), Tuple(stable_status, person_boxes, session_data)
[DB OPS]: self.state_machine.update, self.tracker.update
[SIDE EFFECTS]: smart_logger.log_if_needed"""
        pass

    def draw_ui(self, frame, occupancy_status, person_boxes, session_data=None):
        """Fungsi khusus untuk menggambar kotak di SETIAP frame
----------------------------------------
[INPUT PARAMS]: frame, occupancy_status, person_boxes, session_data
[RETURN SHAPES DETECTED]: Var:frame"""
        pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\hand_activity.py`
```python
import numpy as np
import os
from dotenv import load_dotenv
from logger import smart_logger
NOSE = 0
LEFT_EYE = 1
RIGHT_EYE = 2
LEFT_EAR = 3
RIGHT_EAR = 4
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_HIP = 11
RIGHT_HIP = 12
load_dotenv()
HEAD_DETECTION_METHOD = os.environ.get('HEAD_DETECTION_METHOD', 'hybrid')
FACE_KEYPOINT_CONFIDENCE = float(os.environ.get('FACE_KEYPOINT_CONFIDENCE', '0.3'))
HEAD_BBOX_EXPAND_RATIO = float(os.environ.get('HEAD_BBOX_EXPAND_RATIO', '1.5'))
BARBER_STANDING_THRESHOLD = float(os.environ.get('BARBER_STANDING_THRESHOLD', '0.5'))
BARBER_PROXIMITY_THRESHOLD = float(os.environ.get('BARBER_PROXIMITY_THRESHOLD', '100'))

def get_face_bbox(kpts, confidence_threshold=0.3):
    """Calculate face bounding box from facial keypoints.

Returns:
    tuple: (x_min, y_min, x_max, y_max) or None if not enough keypoints
----------------------------------------
[INPUT PARAMS]: kpts, confidence_threshold
[RETURN SHAPES DETECTED]: Literal:NoneType, Tuple(x_min, y_min, x_max, y_max)"""
    pass

def get_shoulder_avg(kpts, confidence_threshold=0.3):
    """Get average position of shoulders.

Returns:
    tuple: (x, y) or None if shoulders not reliable
----------------------------------------
[INPUT PARAMS]: kpts, confidence_threshold
[RETURN SHAPES DETECTED]: Literal:NoneType, Tuple(x, y)"""
    pass

def get_head_center(kpts, confidence_threshold=0.3, method='hybrid'):
    """Get head center using multiple methods.

Args:
    kpts: keypoints array (17, 3)
    confidence_threshold: minimum confidence for keypoints
    method: 'face_bbox', 'nose', 'shoulder_avg', or 'hybrid'

Returns:
    tuple: (x, y) or None
----------------------------------------
[INPUT PARAMS]: kpts, confidence_threshold, method
[RETURN SHAPES DETECTED]: Literal:NoneType, Tuple(BinOp, BinOp), Tuple(Subscript, BinOp), Tuple(Subscript, Subscript)"""
    pass

def is_barber_for_chair(kpts, track_id, chair_id, rois, tracked_objects, posture_history, confidence_threshold=0.3):
    """Determine if this person is the barber for a given chair.

Returns:
    bool: True if this person is likely the barber
----------------------------------------
[INPUT PARAMS]: kpts, track_id, chair_id, rois, tracked_objects, posture_history, confidence_threshold
[RETURN SHAPES DETECTED]: Literal:bool"""
    pass

def calculate_hand_activity(kpts, prev_kpts=None, frame_height=None, confidence_threshold=0.3, chair_id=None, rois=None, posture_history=None, tracked_objects=None, track_id=None):
    """Hitung poin aktivitas tangan untuk frame saat ini (hanya untuk barber).
----------------------------------------
[INPUT PARAMS]: kpts, prev_kpts, frame_height, confidence_threshold, chair_id, rois, posture_history, tracked_objects, track_id
[RETURN SHAPES DETECTED]: Literal:int, Var:points
[SIDE EFFECTS]: smart_logger.log_if_needed"""
    pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\logger.py`
```python
import os
import sys
import time
import inspect
from datetime import datetime
from loguru import logger
COMPONENT_NAMES = {'SYSTEM': 'system', 'DETECTOR': 'detector', 'TRACK_MANAGER': 'track_manager', 'HAND_ACTIVITY': 'hand_activity', 'POSTURE': 'posture', 'SCORING': 'scoring', 'STATE_MACHINE': 'state_machine', 'NETWORK': 'network', 'ROI_MANAGER': 'roi_manager', 'MAIN': 'main'}
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
LOG_ROTATION = os.environ.get('LOG_ROTATION', '100 MB')
LOG_RETENTION = os.environ.get('LOG_RETENTION', '7 days')
os.makedirs('logs', exist_ok=True)
logger.remove()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logger.add(os.path.join(LOG_DIR, 'ai_engine.jsonl'), format='{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}', level=LOG_LEVEL, rotation=LOG_ROTATION, retention=LOG_RETENTION, serialize=True, enqueue=False)
logger.add(sys.stderr, format='<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>', level=LOG_LEVEL, colorize=True)
print(f"[LOGGER DEBUG] Writing to: {os.path.join(LOG_DIR, 'ai_engine.jsonl')}")
print(f"[LOGGER DEBUG] File exists: {os.path.exists(os.path.join(LOG_DIR, 'ai_engine.jsonl'))}")
_frame_count = 0

def set_frame_count(count):
    """Set global frame count untuk digunakan dalam log
----------------------------------------
[INPUT PARAMS]: count"""
    pass

def get_frame_count():
    """Dapatkan frame count saat ini
----------------------------------------
[RETURN SHAPES DETECTED]: Var:_frame_count"""
    pass

def log_event(component, event, level='INFO', _caller_info=None, **data):
    """Helper untuk menulis log terstruktur.

Args:
    component (str): Nama komponen (harus terdaftar di COMPONENT_NAMES).
    event (str): Nama event log.
    level (str): Level log ('DEBUG', 'INFO', 'WARNING', 'ERROR').
    _caller_info (dict, optional): Informasi caller (file, function, line).
        Jika None, akan dideteksi otomatis via inspect.stack().
        Parameter internal - digunakan oleh SmartLogger agar caller
        yang tercatat adalah modul pemanggil, bukan SmartLogger.
    **data: Field data tambahan yang akan disertakan dalam log.
----------------------------------------
[INPUT PARAMS]: component, event, level, _caller_info
[DB OPS]: log_data.update
[SIDE EFFECTS]: .log, logger.bind, logger.warning"""
    pass

class SmartLogger:
    """Manajemen interval logging per komponen dengan sampling berbasis waktu.

SmartLogger menggantikan sampling berbasis frame (_sample_rate) dengan
sampling berbasis waktu menggunakan ``time.time()``. Ini mengurangi
frekuensi log dari ~7 log/detik menjadi ~0.2 log/detik tanpa kehilangan
data penting, karena semua state changes tetap dicatat secara real-time.

Attributes:
    _log_interval_seconds (float): Interval minimum antar log (default 5 detik).
    _minimal_level (str): Level minimal yang akan ditulis (default 'INFO').
    _aggregate_interval_seconds (float): Interval untuk log metrik agregat (default 60 detik).
    _performance_debug_mode (bool): Jika True, mengaktifkan log DEBUG.
----------------------------------------
[CLASS STATE / ATTRS]: _aggregate_data, _aggregate_interval_seconds, _last_aggregate_time, _last_log_time, _log_interval_seconds, _minimal_level, _performance_debug_mode"""
    _LEVEL_RANK = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40}
    _MAX_RECENT_VALUES = 1200

    def __init__(self):
        """Inisialisasi SmartLogger dengan konfigurasi dari environment variables."""
        pass

    def _record_aggregate(self, component_key, data):
        """Catat data numerik/kategorikal untuk agregasi metrik.

Dipanggil setiap kali log_if_needed dipanggil (termasuk saat log
disampling), sehingga metrik agregat mencakup SEMUA pemrosesan frame,
bukan hanya frame yang dipilih untuk logging.

Args:
    component_key (str): Kunci komponen (misal 'hand_activity').
    data (dict): Data yang akan dicatat untuk agregasi.
----------------------------------------
[INPUT PARAMS]: component_key, data"""
        pass

    def _build_distribution(self, values):
        """Bangun distribusi histogram sederhana dari daftar nilai.

Args:
    values (list): Daftar nilai numerik.

Returns:
    dict: Histogram dengan bucket dan rata-rata, atau None jika kosong.
----------------------------------------
[INPUT PARAMS]: values
[RETURN SHAPES DETECTED]: Dict{ avg, min, max, count, buckets }, Literal:NoneType"""
        pass

    def _log_aggregate(self, component_key, _caller_info=None):
        """Tulis log metrik agregat untuk komponen tertentu.

Metrik agregat ditulis setiap ``_aggregate_interval_seconds`` (default 60 detik)
menggunakan event 'AGGREGATE_METRICS'. Ini memberikan gambaran ringkas
statistik pemrosesan tanpa membanjiri log.

Args:
    component_key (str): Kunci komponen yang akan diagregasi.
    _caller_info (dict, optional): Informasi caller asli yang di-pass
        dari log_if_needed agar file/function/line yang tercatat
        adalah modul pemanggil, bukan SmartLogger.
----------------------------------------
[INPUT PARAMS]: component_key, _caller_info
[SIDE EFFECTS]: log_event"""
        pass

    def _check_aggregate(self, component_key, _caller_info=None):
        """Periksa apakah sudah waktunya menulis metrik agregat.

Args:
    component_key (str): Kunci komponen yang akan diperiksa.
    _caller_info (dict, optional): Informasi caller asli yang di-pass
        dari log_if_needed.
----------------------------------------
[INPUT PARAMS]: component_key, _caller_info
[SIDE EFFECTS]: self._log_aggregate"""
        pass

    def log_if_needed(self, component_key, event, level='INFO', force=False, **data):
        """Tulis log hanya jika interval waktu sudah terpenuhi.

Aturan:
- WARNING/ERROR: Selalu ditulis langsung (tidak disampling).
- DEBUG: Hanya jika ``PERFORMANCE_DEBUG_MODE=true``, lalu disampling.
- INFO: Selalu disampling sesuai ``_log_interval_seconds``.
- force=True: Paksa tulis log meskipun interval belum terpenuhi
  (misal untuk perubahan skor signifikan).

Data agregat selalu dicatat setiap pemanggilan, terlepas dari
apakah log ditulis atau tidak.

Args:
    component_key (str): Kunci unik komponen (misal 'hand_activity').
    event (str): Nama event log (misal 'HAND_ACTIVITY_CALCULATED').
    level (str): Level log ('DEBUG', 'INFO', 'WARNING', 'ERROR').
    force (bool): Jika True, log langsung tanpa menunggu interval.
    **data: Field data tambahan yang akan disertakan dalam log.

Returns:
    bool: True jika log benar-benar ditulis, False jika disampling.
----------------------------------------
[INPUT PARAMS]: component_key, event, level, force
[RETURN SHAPES DETECTED]: Literal:bool
[SIDE EFFECTS]: log_event, logger.warning"""
        pass
smart_logger = SmartLogger()

def check_redis_connection():
    """Cek koneksi Redis.

Returns:
    bool: True jika koneksi berhasil, False jika gagal
----------------------------------------
[RETURN SHAPES DETECTED]: Literal:bool
[SIDE EFFECTS]: log_event, redis.Redis"""
    pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\main.py`
```python
import os
import cv2
import time
import signal
import sys
import redis
from detector import BarberDetector
from utils import load_config, save_config, draw_roi_event
from network import PantauNetwork
from dotenv import load_dotenv
from logger import log_event, check_redis_connection, set_frame_count, smart_logger
load_dotenv()
HEADLESS = os.environ.get('HEADLESS', 'false').lower() == 'true'
if HEADLESS:
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['DISPLAY'] = ':0'
    log_event('system', 'HEADLESS_MODE', level='INFO', mode='enabled')
LATEST_FRAME = None
REDIS_CLIENT = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
RUNNING = True
HEARTBEAT_INTERVAL_FRAMES = int(os.environ.get('HEARTBEAT_INTERVAL_FRAMES', '900'))
SESSION_UPDATE_INTERVAL = int(os.environ.get('SESSION_UPDATE_INTERVAL', '5'))
INFERENCE_LOG_SAMPLE_RATE = int(os.environ.get('INFERENCE_LOG_SAMPLE_RATE', '50'))

def signal_handler(sig, frame):
    """Graceful shutdown kalo di Ctrl+C
----------------------------------------
[INPUT PARAMS]: sig, frame
[SIDE EFFECTS]: log_event"""
    pass

def main():
    """[SIDE EFFECTS]: CHAIR_CONFIG.clear, PantauNetwork, REDIS_CLIENT.setex, check_redis_connection, load_config, log_event, network.report_session_update, network.report_status_change, network.send_heartbeat, save_config, smart_logger.log_if_needed"""
    pass
if __name__ == '__main__':
    main()
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\network.py`
```python
import requests
from logger import log_event, smart_logger

class PantauNetwork:
    """[CLASS STATE / ATTRS]: base_url, end_url, heartbeat_url, start_url, update_url"""

    def __init__(self, base_url='http://localhost:8000'):
        """[INPUT PARAMS]: base_url
[SIDE EFFECTS]: smart_logger.log_if_needed"""
        pass

    def report_status_change(self, chair_id, is_occupied):
        """Mengirim data ke Django hanya saat ada perubahan (binary occupancy)
----------------------------------------
[INPUT PARAMS]: chair_id, is_occupied
[RETURN SHAPES DETECTED]: Literal:bool
[SIDE EFFECTS]: log_event, smart_logger.log_if_needed"""
        pass

    def report_session_update(self, chair_id, is_active, confidence_score, session_status, trigger_reason=None, breakdown=None, timeout_reason=None):
        """Mengirim update sesi lengkap ke Django (state machine integration)
----------------------------------------
[INPUT PARAMS]: chair_id, is_active, confidence_score, session_status, trigger_reason, breakdown, timeout_reason
[RETURN SHAPES DETECTED]: Literal:bool
[SIDE EFFECTS]: log_event, smart_logger.log_if_needed"""
        pass

    def send_heartbeat(self, chair_id, is_active, confidence_score, session_status):
        """Mengirim heartbeat ke Django untuk menjaga sesi tetap hidup
----------------------------------------
[INPUT PARAMS]: chair_id, is_active, confidence_score, session_status
[RETURN SHAPES DETECTED]: Literal:bool
[SIDE EFFECTS]: log_event, smart_logger.log_if_needed"""
        pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\posture_classifier.py`
```python
import os
import numpy as np
from dotenv import load_dotenv
from logger import smart_logger
NOSE = 0
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_HIP = 11
RIGHT_HIP = 12

class PostureClassifier:
    """Posture classification logic using multiple signals.
----------------------------------------
[CLASS STATE / ATTRS]: chair_detection_confidence, keypoint_conf_threshold, sitting_area_ratio_threshold, sitting_min_consistent_frames, sitting_temporal_window"""

    def __init__(self):
        pass

    def classify(self, kpts, bbox=None, roi=None, frame_height=None, chair_id=None, track_id=None):
        """Mengklasifikasikan seseorang sebagai DUDUK atau BERDIRI berdasarkan beberapa sinyal.
----------------------------------------
[INPUT PARAMS]: kpts, bbox, roi, frame_height, chair_id, track_id
[RETURN SHAPES DETECTED]: Literal:str, Var:result
[SIDE EFFECTS]: smart_logger.log_if_needed"""
        pass

    def _calculate_area_ratio(self, bbox):
        """Calculate width/height ratio of person bounding box.
----------------------------------------
[INPUT PARAMS]: bbox"""
        pass

    def _get_consistent_posture(self, posture_history, track_id):
        """Get posture that has been consistent across last N frames.
----------------------------------------
[INPUT PARAMS]: posture_history, track_id
[RETURN SHAPES DETECTED]: Literal:NoneType, Literal:str"""
        pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\roi_manager.py`
```python
class ROIManager:
    """ROI and occupancy management logic.
----------------------------------------
[CLASS STATE / ATTRS]: occupancy_counters, rois, stable_status, threshold_frames"""

    def __init__(self, rois=None):
        """[INPUT PARAMS]: rois"""
        pass

    def update_rois(self, new_rois):
        """[INPUT PARAMS]: new_rois"""
        pass

    def check_occupancy(self, person_box, roi_box):
        """[INPUT PARAMS]: person_box, roi_box"""
        pass

    def update_occupancy(self, person_boxes):
        """Update occupancy status with anti-flickering smoothing.
----------------------------------------
[INPUT PARAMS]: person_boxes
[RETURN SHAPES DETECTED]: Var:self.stable_status"""
        pass

    def count_persons_in_roi(self, person_boxes, chair_id):
        """Count persons in a specific ROI.
----------------------------------------
[INPUT PARAMS]: person_boxes, chair_id
[RETURN SHAPES DETECTED]: Var:count"""
        pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\scoring_engine.py`
```python
import os
import numpy as np
from dotenv import load_dotenv
from logger import smart_logger

class ScoringEngine:
    """Scoring calculation logic for session evaluation.
----------------------------------------
[CLASS STATE / ATTRS]: _last_score, hand_activity_weight, person_count_weight, posture_weight, temporal_weight"""

    def __init__(self):
        pass

    def calculate(self, chair_id, track_manager, rois, duration):
        """Hitung skor sesi keseluruhan untuk suatu kursi.
----------------------------------------
[INPUT PARAMS]: chair_id, track_manager, rois, duration
[RETURN SHAPES DETECTED]: Tuple(total_score_int, Dict)
[SIDE EFFECTS]: smart_logger.log_if_needed"""
        pass

    def calculate_posture_score(self, chair_id, track_manager, rois):
        """Calculate posture score based on sitting/standing combo history.
----------------------------------------
[INPUT PARAMS]: chair_id, track_manager, rois
[RETURN SHAPES DETECTED]: Literal:int"""
        pass

    def calculate_hand_score(self, chair_id, track_manager, rois, tracked_objects=None):
        """Calculate hand activity score (0-100) based on barber's hand activity only.
----------------------------------------
[INPUT PARAMS]: chair_id, track_manager, rois, tracked_objects
[RETURN SHAPES DETECTED]: Literal:int"""
        pass

    def calculate_temporal_score(self, duration):
        """Calculate temporal score based on session duration.
----------------------------------------
[INPUT PARAMS]: duration
[RETURN SHAPES DETECTED]: Literal:int"""
        pass

    def calculate_person_count_score(self, chair_id, track_manager, rois):
        """Calculate person count score based on how often 2 persons are present.
----------------------------------------
[INPUT PARAMS]: chair_id, track_manager, rois
[RETURN SHAPES DETECTED]: Literal:int"""
        pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\state_machine.py`
```python
import os
import time
import numpy as np
from dotenv import load_dotenv
from logger import log_event

class StateMachine:
    """Mesin status untuk manajemen siklus sesi.
----------------------------------------
[CLASS STATE / ATTRS]: confirmation_window, cooldown_seconds, last_breakdown, last_score, last_update, min_valid_duration, pending_duration, pending_start, scores, scoring_threshold, session_timeout_action, session_timeout_seconds, states, timers"""

    def __init__(self):
        pass

    def update(self, chair_id, score, person_count, duration, breakdown=None):
        """Perbarui mesin status untuk kursi tertentu.

Returns:
    tuple: (status_baru, status_berubah, timeout_terjadi, trigger_reason)
----------------------------------------
[INPUT PARAMS]: chair_id, score, person_count, duration, breakdown
[RETURN SHAPES DETECTED]: Tuple(new_state, status_changed, timeout_occurred, trigger_reason)
[SIDE EFFECTS]: log_event"""
        pass

    def check_timeout(self, chair_id):
        """Check if session has been active too long without updates.

Returns:
    bool: True if timeout occurred and action should be taken
----------------------------------------
[INPUT PARAMS]: chair_id
[RETURN SHAPES DETECTED]: Literal:bool"""
        pass

    def get_state(self, chair_id):
        """[INPUT PARAMS]: chair_id"""
        pass

    def get_last_update_time(self, chair_id):
        """[INPUT PARAMS]: chair_id"""
        pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\track_manager.py`
```python
import os
import numpy as np
from dotenv import load_dotenv
from logger import smart_logger

class TrackManager:
    """Tracking data management logic.
----------------------------------------
[CLASS STATE / ATTRS]: _prev_keypoints, cleanup_counter, cleanup_interval, hand_activity, person_types, posture_history, track_last_seen, track_timeout, trajectories"""

    def __init__(self):
        pass

    def update_tracks(self, tracked_objects, keypoints_per_track, rois, frame_height, posture_classifier, hand_activity_func, current_frame=None):
        """[INPUT PARAMS]: tracked_objects, keypoints_per_track, rois, frame_height, posture_classifier, hand_activity_func, current_frame
[SIDE EFFECTS]: smart_logger.log_if_needed"""
        pass

    def identify_barber_for_chair(self, chair_id, rois, tracked_objects):
        """Identify which track_id is the barber for a given chair.

Returns:
    int or None: track_id of barber, or None if not found
----------------------------------------
[INPUT PARAMS]: chair_id, rois, tracked_objects
[RETURN SHAPES DETECTED]: Literal:NoneType"""
        pass

    def get_person_type(self, track_id):
        """Return 'barber', 'customer', or 'unknown'.
----------------------------------------
[INPUT PARAMS]: track_id"""
        pass

    def cleanup(self, current_frame):
        """Remove track data that hasn't been seen for > timeout frames.
----------------------------------------
[INPUT PARAMS]: current_frame"""
        pass

    def get_trajectory(self, track_id):
        """[INPUT PARAMS]: track_id"""
        pass

    def get_posture_history(self, track_id):
        """[INPUT PARAMS]: track_id"""
        pass

    def get_hand_activity(self, track_id):
        """[INPUT PARAMS]: track_id"""
        pass
```

### File: `C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\utils.py`
```python
import json
import cv2
import os
import numpy as np

def load_config(filename='config.json'):
    """[INPUT PARAMS]: filename"""
    pass

def save_config(rois, filename='config.json'):
    """[INPUT PARAMS]: rois, filename"""
    pass
mouse_state = {'drawing': False, 'is_dragging': False, 'ix': -1, 'iy': -1, 'selected_roi_idx': -1}

def draw_roi_event(event, x, y, flags, param):
    """[INPUT PARAMS]: event, x, y, flags, param
[SIDE EFFECTS]: chair_config.append, chair_config.pop, save_config"""
    pass

def compute_iou(box1, box2):
    """Compute Intersection over Union between two bounding boxes.

Args:
    box1, box2: arrays of [x1, y1, x2, y2]
    
Returns:
    float: IoU value
----------------------------------------
[INPUT PARAMS]: box1, box2"""
    pass

def match_keypoints_to_tracked(yolo_boxes, yolo_keypoints, tracked_objects, iou_threshold=0.3):
    """Mencocokkan deteksi YOLO (dengan titik kunci) dengan objek yang dilacak ByteTrack menggunakan IoU.

Argumen:
yolo_boxes: array numpy dengan bentuk (N, 4) berisi kotak deteksi YOLO
yolo_keypoints: array numpy dengan bentuk (N, 17, 3) berisi titik kunci
tracked_objects: daftar objek ByteTrack
iou_threshold: IoU minimum untuk mempertimbangkan kecocokan

Hasil:
dict: track_id -> array titik kunci untuk objek yang cocok
----------------------------------------
[INPUT PARAMS]: yolo_boxes, yolo_keypoints, tracked_objects, iou_threshold
[RETURN SHAPES DETECTED]: Var:matched"""
    pass
```
