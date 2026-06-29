import cv2
import time
from detector import BarberDetector
from utils import load_config, save_config, draw_roi_event
from network import PantauNetwork

LATEST_FRAME = None

def main():
    global LATEST_FRAME
    print("\n" + "=" * 40)
    print("      PANTAUCUKUR AI ENGINE v1.0      ")
    print("=" * 40)

    STREAM_URL = "http://192.168.1.7:8080/video"

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

    # 2. Setup Window & Mouse Callback
    cv2.namedWindow("PantauCukur AI Dashboard")
    callback_params = [CHAIR_CONFIG, last_status, detector]
    cv2.setMouseCallback("PantauCukur AI Dashboard", draw_roi_event, callback_params)

    print(f"[SYSTEM] Menghubungkan ke kamera: {STREAM_URL}...")
    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        print("[ERROR] Gagal membuka stream! Pastikan IP Webcam aktif.")
        return

    print("[SUCCESS] Engine Berjalan. Tekan 'q' untuk keluar, 'c' untuk reset ROI.")
    print("-" * 40)

    frame_count = 0
    skip_frames = 10

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Frame kosong atau stream terputus. Mencoba ulang...")
            time.sleep(0.1)
            continue

        LATEST_FRAME = frame.copy()

        frame_count += 1

        # 1. Logika AI (Setiap 10 frame)
        if frame_count % skip_frames == 0:
            # Update deteksi AI
            new_status, last_boxes = detector.process_ai(frame)

            # Sinkronisasi jumlah list jika ada penambahan ROI secara dinamis
            while len(last_status) < len(new_status):
                last_status.append(False)

            # --- LOGIKA MODULAR NETWORK & STATE MONITORING ---
            for i in range(len(new_status)):
                if i < len(last_status):
                    # Bandingkan status baru dengan memori lama
                    if new_status[i] != last_status[i]:
                        status_str = "TERISI" if new_status[i] else "KOSONG"
                        print(f"[EVENT] Perubahan Status - Kursi {i+1}: {status_str}")

                        # Kirim ke Django
                        network.report_status_change(i + 1, new_status[i])

                        # Update memori status setelah dibandingkan
                        last_status[i] = new_status[i]
            # ------------------------------------------

        # 2. Logika UI
        processed_frame = detector.draw_ui(frame, last_status, last_boxes)

        cv2.putText(
            processed_frame,
            f"AI Refresh: 1/{skip_frames} frames",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )

        cv2.imshow("PantauCukur AI Dashboard", processed_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            print("[SYSTEM] Mematikan Engine... Sampai jumpa, Pii!")
            break
        elif key == ord("c"):
            print("[ACTION] Melakukan reset ROI kursi...")
            CHAIR_CONFIG.clear()
            last_status.clear()
            detector.update_rois(CHAIR_CONFIG)
            save_config(CHAIR_CONFIG)
            print("[SUCCESS] Konfigurasi dibersihkan.")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
