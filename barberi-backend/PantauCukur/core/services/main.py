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
from logger import log_event, check_redis_connection, set_frame_count

# ============================================================
# HEADLESS MODE - Matikan GUI kalau di server
# ============================================================

load_dotenv()
HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"

if HEADLESS:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["DISPLAY"] = ":0"
    log_event("system", "HEADLESS_MODE", level="INFO", mode="enabled")

# Global variable buat Django
LATEST_FRAME = None
REDIS_CLIENT = redis.Redis(host="localhost", port=6379, db=0, decode_responses=False)
RUNNING = True

# Konfigurasi heartbeat
HEARTBEAT_INTERVAL_FRAMES = int(os.environ.get("HEARTBEAT_INTERVAL_FRAMES", "900"))  # 30 detik pada 30fps
SESSION_UPDATE_INTERVAL = int(os.environ.get("SESSION_UPDATE_INTERVAL", "5"))  # frame

# Konfigurasi logging
INFERENCE_LOG_SAMPLE_RATE = int(os.environ.get("INFERENCE_LOG_SAMPLE_RATE", "50"))

def signal_handler(sig, frame):
    """Graceful shutdown kalo di Ctrl+C"""
    global RUNNING
    log_event("system", "SIGNAL_RECEIVED", level="INFO", signal=sig)
    RUNNING = False

def main():
    global LATEST_FRAME, RUNNING

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # ============================================================
    # ENGINE START EVENT
    # ============================================================
    STREAM_URL = os.environ.get("CAMERA_URL", "http://192.168.1.155:8080/video")
    SKIP_FRAMES = int(os.environ.get("SKIP_FRAMES", 10))
    use_scoring = os.environ.get("USE_SCORING", "true").lower() == "true"
    
    # Cek koneksi Redis
    redis_connected = check_redis_connection()
    
    # Load config
    CHAIR_CONFIG = load_config()
    
    log_event("system", "ENGINE_START", level="INFO",
              headless_mode=HEADLESS,
              camera_url=STREAM_URL,
              skip_frames=SKIP_FRAMES,
              use_scoring=use_scoring,
              roi_count=len(CHAIR_CONFIG),
              redis_connected=redis_connected)

    session_data = {}

    # 1. Inisialisasi Data
    log_event("system", "CONFIG_LOADED", level="INFO", roi_count=len(CHAIR_CONFIG))

    log_event("system", "MODEL_LOADING", level="INFO")
    detector = BarberDetector(rois=CHAIR_CONFIG)
    log_event("system", "MODEL_LOADED", level="INFO")

    log_event("system", "NETWORK_INIT", level="INFO")
    network = PantauNetwork()

    last_status = [False] * len(CHAIR_CONFIG)
    last_boxes = []
    last_session_data = {}  # Simpan session_data terakhir untuk heartbeat

    # ============================================================
    # SETUP WINDOW (Cuma kalau tidak headless)
    # ============================================================
    if not HEADLESS:
        cv2.namedWindow("PantauCukur AI Dashboard")
        callback_params = [CHAIR_CONFIG, last_status, detector]
        cv2.setMouseCallback(
            "PantauCukur AI Dashboard", draw_roi_event, callback_params
        )
    else:
        log_event("system", "HEADLESS_MODE", level="INFO", mode="enabled")

    # ============================================================
    # CONNECT TO CAMERA
    # ============================================================
    log_event("system", "CAMERA_CONNECTING", level="INFO", stream_url=STREAM_URL)
    cap = cv2.VideoCapture(STREAM_URL)

    # Setting buffer kecil buat kurangi delay
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        log_event("error", "CAMERA_OPEN_FAILED", level="ERROR", stream_url=STREAM_URL)
        return

    log_event("system", "ENGINE_RUNNING", level="INFO",
              headless=HEADLESS,
              skip_frames=SKIP_FRAMES)

    frame_count = 0
    reconnect_attempts = 0
    max_reconnect_attempts = 5
    start_time = time.time()
    last_heartbeat_time = time.time()
    last_inference_time = time.time()
    last_person_count = 0

    while RUNNING:
        try:
            ret, frame = cap.read()

            # ============================================================
            # RECONNECT LOGIC
            # ============================================================
            if not ret:
                reconnect_attempts += 1
                log_event("warning", "FRAME_DROP", level="WARNING",
                          reconnect_attempts=reconnect_attempts,
                          frame_count=frame_count,
                          stream_url=STREAM_URL)

                if reconnect_attempts >= max_reconnect_attempts:
                    log_event("error", "MAX_RECONNECT_ATTEMPTS", level="ERROR",
                              attempts=reconnect_attempts)
                    cap.release()
                    time.sleep(1)
                    cap = cv2.VideoCapture(STREAM_URL)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    reconnect_attempts = 0
                    log_event("system", "STREAM_RECONNECTED", level="INFO",
                              stream_url=STREAM_URL)

                time.sleep(0.1)
                continue

            reconnect_attempts = 0  # Reset kalo sukses

            # ============================================================
            # SAVE LATEST FRAME (buat Django)
            # ============================================================
            # Compress frame to JPEG (reduce size)
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])

            # Store in Redis with 5-second expiry
            REDIS_CLIENT.setex("latest_frame", 5, buffer.tobytes())
            frame_count += 1
            set_frame_count(frame_count)

            # ============================================================
            # AI PROCESSING (Skip beberapa frame biar ringan)
            # ============================================================
            if frame_count % SKIP_FRAMES == 0:
                # Ukur waktu inferensi
                inference_start = time.time()
                
                if use_scoring:
                    new_status, last_boxes, session_data = detector.process_ai(frame)
                else:
                    new_status, last_boxes, session_data = detector.process_ai(frame)
                    # session_data = {}

                inference_time_ms = (time.time() - inference_start) * 1000

                # Sinkronisasi jumlah list
                while len(last_status) < len(new_status):
                    last_status.append(False)

                # ============================================================
                # INFERENCE COMPLETE EVENT (sampling)
                # ============================================================
                if frame_count % INFERENCE_LOG_SAMPLE_RATE == 0:
                    person_count_delta = len(new_status) - last_person_count
                    log_event("system", "INFERENCE_COMPLETE", level="INFO",
                              inference_time_ms=round(inference_time_ms, 2),
                              person_count_delta=person_count_delta)
                    last_person_count = len(new_status)

                # ============================================================
                # NETWORK & STATE MONITORING - Kirim perubahan ke Django
                # ============================================================
                for i in range(len(new_status)):
                    chair_id = i + 1  # 1-indexed untuk API
                    
                    # 1. Kirim status occupancy (binary) jika berubah
                    if i < len(last_status) and new_status[i] != last_status[i]:
                        status_str = "TERISI" if new_status[i] else "KOSONG"
                        log_event("event", "STATUS_CHANGE", level="INFO",
                                  chair_id=chair_id,
                                  status=status_str)

                        # Kirim ke Django (binary occupancy)
                        success = network.report_status_change(chair_id, new_status[i])
                        if not success:
                            log_event("warning", "STATUS_SEND_FAILED", level="WARNING",
                                      chair_id=chair_id)

                        # Update memori
                        last_status[i] = new_status[i]
                    
                    # 2. Kirim session update jika ada perubahan status state machine
                    if use_scoring and session_data and i in session_data:
                        sd = session_data[i]
                        if sd.get('status_changed', False):
                            log_event("event", "STATE_MACHINE_CHANGE", level="INFO",
                                      chair_id=chair_id,
                                      session_status=sd['session_status'],
                                      confidence_score=sd['confidence_score'])
                            
                            # Kirim session update ke Django
                            success = network.report_session_update(
                                chair_id=chair_id,
                                is_active=sd['is_active'],
                                confidence_score=sd['confidence_score'],
                                session_status=sd['session_status']
                            )
                            if not success:
                                log_event("warning", "SESSION_UPDATE_FAILED", level="WARNING",
                                          chair_id=chair_id)
                        
                        # Simpan session_data terakhir untuk heartbeat
                        last_session_data[i] = sd
                
                # 3. Heartbeat: kirim keepalive ke Django secara periodik
                if use_scoring and frame_count % HEARTBEAT_INTERVAL_FRAMES == 0:
                    for i in range(len(new_status)):
                        if i in last_session_data:
                            sd = last_session_data[i]
                            network.send_heartbeat(
                                chair_id=i + 1,
                                is_active=sd.get('is_active', False),
                                confidence_score=sd.get('confidence_score', 0),
                                session_status=sd.get('session_status', 'IDLE')
                            )

            # ============================================================
            # HEARTBEAT EVENT (setiap 500 frame)
            # ============================================================
            if frame_count % 500 == 0:
                uptime_seconds = time.time() - start_time
                fps_actual = frame_count / uptime_seconds if uptime_seconds > 0 else 0
                active_sessions = sum(1 for sd in last_session_data.values() if sd.get('is_active', False))
                redis_connected = check_redis_connection()
                
                log_event("system", "HEARTBEAT", level="INFO",
                          uptime_seconds=round(uptime_seconds, 2),
                          fps_actual=round(fps_actual, 2),
                          active_sessions=active_sessions,
                          redis_connected=redis_connected)

            # ============================================================
            # UI DRAWING
            # ============================================================
            processed_frame = detector.draw_ui(frame, last_status, last_boxes)

            # --- INFO DASAR ---
            y_pos = 30
            cv2.putText(
                processed_frame,
                f"AI Refresh: 1/{SKIP_FRAMES} frames | Frames: {frame_count}",
                (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 255),
                1,
            )

            # --- TAMPILKAN SCORING REAL-TIME (jika USE_SCORING=true) ---
            if use_scoring and session_data:
                y_pos = 60
                for i, sd in session_data.items():
                    chair_id = i + 1
                    score = sd.get('confidence_score', 0)
                    status = sd.get('session_status', 'IDLE')
                    breakdown = sd.get('score_breakdown', {})
                    
                    text = f"K{chair_id}: {score} | {status} | Posture: {breakdown.get('posture',0)} Hand_Act: {breakdown.get('hand_activity',0)} Temporal: {breakdown.get('temporal',0)} Person_Count: {breakdown.get('person_count',0)}"

                    y_pos += 4
                    cv2.putText(
                        processed_frame,
                        text,
                        (10, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 255) if status == 'ACTIVE' else (255, 255, 255),
                        1,
                    )
                    y_pos += 25

            # ============================================================
            # SHOW (Cuma kalau ada GUI)
            # ============================================================
            if not HEADLESS:
                cv2.imshow("PantauCukur AI Dashboard", processed_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    log_event("system", "ENGINE_STOPPED", level="INFO", reason="user_quit")
                    RUNNING = False
                    break
                elif key == ord("c"):
                    log_event("action", "ROI_RESET", level="INFO")
                    CHAIR_CONFIG.clear()
                    last_status.clear()
                    detector.update_rois(CHAIR_CONFIG)
                    save_config(CHAIR_CONFIG)
                    log_event("system", "ROI_RESET_COMPLETE", level="INFO")
            else:
                # Headless: kasih tau masih hidup
                if frame_count % 500 == 0:
                    log_event("system", "HEADLESS_HEARTBEAT", level="INFO",
                              frame_count=frame_count)

        except Exception as e:
            log_event("error", "UNEXPECTED_ERROR", level="ERROR", error=str(e))
            time.sleep(0.5)

    # ============================================================
    # CLEANUP
    # ============================================================
    log_event("system", "CLEANUP_START", level="INFO")
    cap.release()
    cv2.destroyAllWindows()
    log_event("system", "ENGINE_STOPPED", level="INFO", reason="cleanup")
    print("[SYSTEM] Engine stopped. Bye!")


if __name__ == "__main__":
    main()
