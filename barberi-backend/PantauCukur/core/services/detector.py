# detector.py
import cv2
from ultralytics import YOLO

class BarberDetector:
    def __init__(self, model_path='yolov8n.pt', rois=None):
        print("Sistem AI: Memuat model...")
        self.model = YOLO(model_path)
        self.rois = rois if rois else []
        self.conf_threshold = 0.5
        # --- FITUR ANTI-FLICKERING ---
        self.occupancy_counters = [0] * len(self.rois)
        self.threshold_frames = 5 # Jeda frame sebelum status berubah
        self.stable_status = [False] * len(self.rois)

    def update_rois(self, new_rois):
        self.rois = new_rois
        print(f"ROI diperbarui: {len(self.rois)} kursi terdaftar.")

    def check_occupancy(self, person_box, roi_box):
        px1, py1, px2, py2 = person_box
        rx1, ry1, rx2, ry2 = roi_box

        # 1. Hitung koordinat tumpang tindih (intersection)
        ix1 = max(px1, rx1)
        iy1 = max(py1, ry1)
        ix2 = min(px2, rx2)
        iy2 = min(py2, ry2)

        # 2. Hitung luas area tumpang tindih
        width = max(0, ix2 - ix1)
        height = max(0, iy2 - iy1)
        intersection_area = width * height

        # 3. Hitung luas kotak kursi (ROI)
        roi_area = (rx2 - rx1) * (ry2 - ry1)

        # 4. Tentukan ambang batas (contoh: 40% dari luas kursi harus tertutup)
        occupancy_ratio = intersection_area / roi_area if roi_area > 0 else 0
    
        return occupancy_ratio > 0.4  # Ubah angka ini (0.1 - 0.9) sesuai selera sensitivitasmu

    def process_ai(self, frame):
        results = self.model(frame, classes=0, conf=self.conf_threshold, verbose=False)
        person_boxes = results[0].boxes.xyxy.cpu().numpy()
        
        # 1. Deteksi mentah (raw) saat ini
        current_raw_status = [False] * len(self.rois)
        for box in person_boxes:
            for i, roi in enumerate(self.rois):
                if self.check_occupancy(box, roi):
                    current_raw_status[i] = True
        
        # 2. Logika Smoothing (Jeda) anti Flickering
        for i in range(len(self.rois)):
            if current_raw_status[i]:
                # Jika terdeteksi, naikkan counter
                self.occupancy_counters[i] = min(self.occupancy_counters[i] + 1, self.threshold_frames + 1)
            else:
                # Jika hilang, turunkan counter
                self.occupancy_counters[i] = max(self.occupancy_counters[i] - 1, 0)

            # Tentukan status stabil
            if self.occupancy_counters[i] >= self.threshold_frames:
                self.stable_status[i] = True
            elif self.occupancy_counters[i] == 0:
                self.stable_status[i] = False
        
        return self.stable_status, person_boxes

    def draw_ui(self, frame, occupancy_status, person_boxes):
        """Fungsi khusus untuk menggambar kotak di SETIAP frame"""
        # Gambar Bounding Box Orang (Opsional)
        for box in person_boxes:
            cv2.rectangle(frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (255, 100, 0), 1)

        # Gambar ROI Kursi
        for i, is_occupied in enumerate(occupancy_status):
            roi = self.rois[i]
            color = (0, 255, 0) if is_occupied else (0, 0, 255)
            status_text = "TERISI" if is_occupied else "KOSONG"

            cv2.rectangle(frame, (roi[0], roi[1]), (roi[2], roi[3]), color, 2)
            cv2.putText(frame, f"Kursi {i+1}: {status_text}", (roi[0], roi[1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        return frame
        