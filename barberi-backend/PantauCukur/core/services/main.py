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

# ============================================================
# HEADLESS MODE - Matikan GUI kalau di server
# ============================================================

load_dotenv()
HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"

if HEADLESS:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["DISPLAY"] = ":0"
    print("[SYSTEM] Running in HEADLESS mode (no GUI)")

# Global variable buat Django
LATEST_FRAME = None
REDIS_CLIENT = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
RUNNING = True


def signal_handler(sig, frame):
    """Graceful shutdown kalo di Ctrl+C"""
    global RUNNING
    print("\n[SYSTEM] Received interrupt signal. Shutting down gracefully...")
    RUNNING = False


def main():
    global LATEST_FRAME, RUNNING

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("\n" + "=" * 40)
    print("      PANTAUCUKUR AI ENGINE v1.0      ")
    print("=" * 40)

    # ============================================================
    # CONFIG - Bisa dari env variable
    # ============================================================
    STREAM_URL = os.environ.get("CAMERA_URL", "http://192.168.1.7:8080/video")
    SKIP_FRAMES = int(os.environ.get("SKIP_FRAMES", 10))

    # 1. Inisialisasi Data
    print("[SYSTEM] Menginisialisasi konfigurasi kursi...")
    CHAIR_CONFIG = load_config()
    print(f"[SYSTEM] {len(CHAIR_CONFIG)} kursi dimuat dari config.")

    print("[SYSTEM] Memuat Model AI YOLOv8...")
    detector = BarberDetector(rois=CHAIR_CONFIG)

    print("[SYSTEM] Mengaktifkan jalur API Network...")
    network = PantauNetwork()

    last_status = [False] * len(CHAIR_CONFIG)
    last_boxes = []

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
        print("[SYSTEM] Headless mode: GUI disabled")

    # ============================================================
    # CONNECT TO CAMERA
    # ============================================================
    print(f"[SYSTEM] Menghubungkan ke kamera: {STREAM_URL}...")
    cap = cv2.VideoCapture(STREAM_URL)

    # Setting buffer kecil buat kurangi delay
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("[ERROR] Gagal membuka stream! Pastikan IP Webcam aktif.")
        return

    print("[SUCCESS] Engine Berjalan.")
    print(f"  - Mode: {'HEADLESS' if HEADLESS else 'GUI'}")
    print(f"  - Skip frames: {SKIP_FRAMES}")
    print("  - Tekan 'q' untuk keluar, 'c' untuk reset ROI.")
    print("-" * 40)

    frame_count = 0
    reconnect_attempts = 0
    max_reconnect_attempts = 5

    while RUNNING:
        try:
            ret, frame = cap.read()

            # ============================================================
            # RECONNECT LOGIC
            # ============================================================
            if not ret:
                reconnect_attempts += 1
                print(
                    f"[WARN] Frame kosong ({reconnect_attempts}/{max_reconnect_attempts})..."
                )

                if reconnect_attempts >= max_reconnect_attempts:
                    print("[ERROR] Max reconnect attempts reached. Reconnecting...")
                    cap.release()
                    time.sleep(1)
                    cap = cv2.VideoCapture(STREAM_URL)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    reconnect_attempts = 0

                time.sleep(0.1)
                continue

            reconnect_attempts = 0  # Reset kalo sukses

            # ============================================================
            # SAVE LATEST FRAME (buat Django)
            # ============================================================
            # Compress frame to JPEG (reduce size)
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            # Store in Redis with 5-second expiry
            REDIS_CLIENT.setex('latest_frame', 5, buffer.tobytes())

            frame_count += 1

            # ============================================================
            # AI PROCESSING (Skip beberapa frame biar ringan)
            # ============================================================
            if frame_count % SKIP_FRAMES == 0:
                new_status, last_boxes = detector.process_ai(frame)

                # Sinkronisasi jumlah list
                while len(last_status) < len(new_status):
                    last_status.append(False)

                # ============================================================
                # NETWORK & STATE MONITORING - Kirim perubahan ke Django
                # ============================================================
                for i in range(len(new_status)):
                    if i < len(last_status) and new_status[i] != last_status[i]:
                        status_str = "TERISI" if new_status[i] else "KOSONG"
                        print(f"[EVENT] Perubahan Status - Kursi {i+1}: {status_str}")

                        # Kirim ke Django
                        success = network.report_status_change(i + 1, new_status[i])
                        if not success:
                            print(f"[WARN] Gagal kirim status kursi {i+1} ke server")

                        # Update memori
                        last_status[i] = new_status[i]

            # ============================================================
            # UI DRAWING
            # ============================================================
            processed_frame = detector.draw_ui(frame, last_status, last_boxes)

            cv2.putText(
                processed_frame,
                f"AI Refresh: 1/{SKIP_FRAMES} frames | Frames: {frame_count}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

            # ============================================================
            # SHOW (Cuma kalau ada GUI)
            # ============================================================
            if not HEADLESS:
                cv2.imshow("PantauCukur AI Dashboard", processed_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("[SYSTEM] Mematikan Engine...")
                    RUNNING = False
                    break
                elif key == ord("c"):
                    print("[ACTION] Melakukan reset ROI kursi...")
                    CHAIR_CONFIG.clear()
                    last_status.clear()
                    detector.update_rois(CHAIR_CONFIG)
                    save_config(CHAIR_CONFIG)
                    print("[SUCCESS] Konfigurasi dibersihkan.")
            else:
                # Headless: kasih tau masih hidup
                if frame_count % 100 == 0:
                    print(f"[HEARTBEAT] Running... {frame_count} frames processed")

        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            time.sleep(0.5)

    # ============================================================
    # CLEANUP
    # ============================================================
    print("[SYSTEM] Cleaning up...")
    cap.release()
    cv2.destroyAllWindows()
    print("[SYSTEM] Engine stopped. Bye!")


if __name__ == "__main__":
    main()
