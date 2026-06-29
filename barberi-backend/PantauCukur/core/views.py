from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import BarberSession
import json
import cv2
import base64
import redis
from .services.utils import load_config, save_config

REDIS_CLIENT = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)

@csrf_exempt
def start_session(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            chair_id = data.get('chair_id')

            # 1. Logika Database
            session = BarberSession.objects.create(chair_number=chair_id)

            # 2. Logika Real-time (Kirim ke Broker/Redis)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "pantau_cukur_events",
                {
                    "type": "send_status_update", 
                    "message": f"Kursi {chair_id} mulai terisi",
                    "chair_id": chair_id,
                    "is_occupied": True
                }
            )

            return JsonResponse({
                "status": "success", 
                "session_id": session.id,
                "message": f"Sesi kursi {chair_id} dimulai"
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

@csrf_exempt
def end_session(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            chair_id = data.get('chair_id')

            # 1. Cari sesi aktif
            session = BarberSession.objects.filter(
                chair_number=chair_id, 
                end_time__isnull=True
            ).last()

            if session:
                # 2. Update waktu dan durasi
                session.end_time = timezone.now()
                delta = session.end_time - session.start_time
                session.duration_seconds = int(delta.total_seconds())

                # 3. Validasi durasi (Logika bisnis kamu)
                if session.duration_seconds > 16: # Pastikan angka ini realistis nanti
                    session.is_valid = True
                
                session.save()

                # 4. Kirim notifikasi real-time bahwa kursi sekarang KOSONG
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "pantau_cukur_events",
                    {
                        "type": "send_status_update",
                        "message": f"Kursi {chair_id} selesai. Durasi: {session.duration_seconds}s",
                        "chair_id": chair_id,
                        "is_occupied": False
                    }
                )

                return JsonResponse({
                    "status": "success", 
                    "duration": session.duration_seconds,
                    "is_valid": session.is_valid
                })

            return JsonResponse({"status": "error", "message": "No active session found"}, status=404)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
        
def get_current_summary_data():
    """Fungsi pembantu untuk mengambil summary yang konsisten"""
    sessions = BarberSession.objects.all().order_by('-start_time')
    valid_sessions = sessions.filter(is_valid=True)
    invalid_sessions = sessions.filter(is_valid=False)

    return {
        "summary": {
            "total_valid": valid_sessions.count(),
            "total_invalid": invalid_sessions.count(),
        },
        "valid_list": [serialize_session(s) for s in valid_sessions[:10]], # Limit 10 agar tidak berat
        "invalid_list": [serialize_session(s) for s in invalid_sessions[:10]]
    }

def serialize_session(s):
    return {
        "id": s.id,
        "chair": s.chair_number,
        "start": s.start_time.isoformat(),
        "duration": s.duration_seconds,
        "status": "VALID" if s.is_valid else "INVALID"
    }

def get_sessions_summary(request):
    if request.method == 'GET':
        data = get_current_summary_data()
        return JsonResponse(data)

@csrf_exempt
def get_camera_frame(request):
    if request.method == 'GET':
        try:
            frame_bytes = REDIS_CLIENT.get('latest_frame')
            if frame_bytes is None:
                return JsonResponse({"status": "error", "message": "No frame available"}, status=503)
            frame_b64 = base64.b64encode(frame_bytes).decode('utf-8')
            rois = load_config()
            return JsonResponse({
                "status": "success",
                "frame": frame_b64,
                "rois": rois
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def update_roi(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rois = data.get('rois', [])
            # Validasi format ROI
            for roi in rois:
                if not isinstance(roi, list) or len(roi) != 4:
                    raise ValueError("Each ROI must be a list of 4 integers")
                for coord in roi:
                    if not isinstance(coord, (int, float)):
                        raise ValueError("Each coordinate must be a number")
            save_config(rois)
            return JsonResponse({"status": "success", "message": "ROIs updated"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
