import cv2
import time
from BARBERI.backend.PantauCukur.core.services.detector import BarberDetector
from BARBERI.backend.PantauCukur.core.services.utils import load_config, save_config, draw_roi_event
from BARBERI.backend.PantauCukur.core.services.network import PantauNetwork  # 1. Impor modul baru

def main():
    STREAM_URL = "http://192.168.1.7:8080/video"
    
    CHAIR_CONFIG = load_config()
    detector = BarberDetector(rois=CHAIR_CONFIG)
    network = PantauNetwork() # 2. Inisialisasi network
    
    # State memori untuk mendeteksi PERUBAHAN
    last_status = [False] * len(CHAIR_CONFIG)
    last_boxes = []

    cv2.namedWindow('PantauCukur AI Dashboard')
    callback_params = [CHAIR_CONFIG, last_status, detector]
    cv2.setMouseCallback('PantauCukur AI Dashboard', draw_roi_event, callback_params)
    
    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        print("Gagal membuka stream!")
        return

    print("PantauCukur Engine Berjalan...")

    frame_count = 0
    skip_frames = 10 

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        frame_count += 1

        # 1. Logika AI (Setiap 10 frame)
        if frame_count % skip_frames == 0:
            new_status, last_boxes = detector.process_ai(frame)
            
            # --- LOGIKA MODULAR NETWORK (DIPERBAIKI) ---
            # Pastikan panjang last_status sama dengan new_status (jika ada penambahan kursi)
            while len(last_status) < len(new_status):
                last_status.append(False)

            for i in range(len(new_status)):
                # Bandingkan status baru dengan memori lama
                if new_status[i] != last_status[i]:
                    # Kirim data ke Django
                    network.report_status_change(i + 1, new_status[i])
                    # Update memori status HANYA setelah dibandingkan
                    last_status[i] = new_status[i]
            # ------------------------------------------

        # 2. Logika UI
        processed_frame = detector.draw_ui(frame, last_status, last_boxes)
        cv2.putText(processed_frame, f"AI Refresh: 1/{skip_frames} frames", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow('PantauCukur AI Dashboard', processed_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            CHAIR_CONFIG.clear()
            last_status.clear()
            detector.update_rois(CHAIR_CONFIG)
            save_config(CHAIR_CONFIG)
            print("Reset Berhasil!")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()