# C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\detector.py
import cv2
import os
import numpy as np
import time  # ← TAMBAHKAN
from ultralytics import YOLO
# from boxmot import ByteTrack  # ← HAPUS
from dotenv import load_dotenv

from state_machine import StateMachine
from scoring_engine import ScoringEngine
from posture_classifier import PostureClassifier
from hand_activity import calculate_hand_activity
from track_manager import TrackManager
from roi_manager import ROIManager
from utils import match_keypoints_to_tracked
from logger import smart_logger


# ==================== SIMPLE TRACKER (TAMBAHKAN) ====================
class SimpleByteTrack:
    """Simple tracker replacement for ByteTrack"""
    def __init__(self, track_thresh=0.5, match_thresh=0.4, frame_rate=30):
        self.track_thresh = track_thresh
        self.match_thresh = match_thresh
        self.frame_rate = frame_rate
        self.tracks = {}
        self.next_id = 0
        self.max_age = 30
        self.min_hits = 3
        self.grace_period = 5  # Frame grace untuk track baru sebelum dievaluasi hits
        
    def update(self, boxes):
        detections = []
        for box in boxes:
            detections.append({
                'box': box,
                'centroid': ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            })
        
        for track_id in list(self.tracks.keys()):
            self.tracks[track_id]['age'] += 1
            
        matched = set()
        for i, det in enumerate(detections):
            best_iou = 0
            best_id = None
            
            for track_id, track in self.tracks.items():
                if track_id in matched:
                    continue
                iou = self._calculate_iou(track['box'], det['box'])
                if iou > self.match_thresh and iou > best_iou:
                    best_iou = iou
                    best_id = track_id
            
            if best_id is not None:
                self.tracks[best_id]['box'] = det['box']
                self.tracks[best_id]['age'] = 0
                self.tracks[best_id]['hits'] += 1
                matched.add(best_id)
            else:
                self.tracks[self.next_id] = {
                    'box': det['box'],
                    'age': 0,
                    'hits': 1,
                    'track_id': self.next_id
                }
                self.next_id += 1
        
        to_remove = []
        for track_id, track in self.tracks.items():
            # Hapus track yang terlalu lama tidak terlihat (timeout)
            if track['age'] > self.max_age:
                to_remove.append(track_id)
                continue
            
            # PERBAIKAN BUG: Grace period untuk track baru.
            # Track baru dibuat dengan hits=1. Jika langsung dihapus karena
            # hits < min_hits, SEMUA track akan hilang setiap frame (BUG).
            # Track hanya dihapus jika sudah melewati grace_period namun hits-nya
            # masih di bawah min_hits (artinya jarang terdeteksi/matching gagal).
            if track['age'] > self.grace_period and track['hits'] < self.min_hits:
                to_remove.append(track_id)
        
        for track_id in to_remove:
            del self.tracks[track_id]
        
        return [TrackObject(track) for track in self.tracks.values()]
    
    def _calculate_iou(self, box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0


class TrackObject:
    """Mock BoxMot track object"""
    def __init__(self, track_data):
        self.track_id = track_data['track_id']
        self.xyxy = track_data['box']
        self.confidence = 1.0
        self.age = track_data['age']
# ================================================================


class BarberDetector:
    def __init__(self, model_path='yolov8n-pose.pt', rois=None):
        print("Sistem AI: Memuat model...")
        self.model = YOLO(model_path)
        self.conf_threshold = 0.5
        
        # GANTI dengan SimpleByteTrack
        # self.tracker = ByteTrack()  # ← COMMENT
        self.tracker = SimpleByteTrack()  # ← GANTI
        
        # Load config
        load_dotenv()
        self.use_scoring = os.environ.get('USE_SCORING', 'false').lower() == 'true'
        
        # Initialize managers
        self.roi_manager = ROIManager(rois)
        self.track_manager = TrackManager()
        self.state_machine = StateMachine()
        self.scoring_engine = ScoringEngine()
        self.posture_classifier = PostureClassifier()
        
        self.frame_count = 0
        self.rois = rois if rois else []
        
        print("Sistem AI: Model siap dengan YOLO-Pose, SimpleTracker, dan Scoring Engine.")
    
    def update_rois(self, new_rois):
        self.rois = new_rois
        self.roi_manager.update_rois(new_rois)
        print(f"ROI diperbarui: {len(self.rois)} kursi terdaftar.")
    
    def process_ai(self, frame):
        """Memproses frame dengan deteksi AI, pelacakan, estimasi pose, dan penilaian.
        
        Returns:
            tuple: (stable_status, person_boxes, session_data) jika USE_SCORING=True
                (stable_status, person_boxes) jika USE_SCORING=False
        """
        start_time = time.time()  # ← TAMBAHKAN untuk processing time
        self.frame_count += 1
        
        # --- Deteksi YOLO (dengan keypoints) ---
        results = self.model(frame, classes=0, conf=self.conf_threshold, verbose=False)
        person_boxes = results[0].boxes.xyxy.cpu().numpy()
        
        # Ekstrak keypoints dari model YOLO-Pose
        yolo_keypoints = None
        if results[0].keypoints is not None:
            yolo_keypoints = results[0].keypoints.xy.cpu().numpy()  # bentuk (N, 17, 2)
            yolo_keypoints_conf = results[0].keypoints.conf.cpu().numpy()  # bentuk (N, 17)
            # Gabungkan xy dan confidence menjadi (N, 17, 3)
            yolo_keypoints = np.concatenate([yolo_keypoints, yolo_keypoints_conf[..., np.newaxis]], axis=-1)
        
        # --- Pelacakan ByteTrack ---
        tracked_objects = self.tracker.update(person_boxes)
        
        # --- Cocokkan keypoints YOLO ke objek yang dilacak ---
        frame_height = frame.shape[0]
        keypoints_per_track = {}
        if yolo_keypoints is not None and len(tracked_objects) > 0:
            keypoints_per_track = match_keypoints_to_tracked(
                person_boxes, yolo_keypoints, tracked_objects
            )
        
        # --- Perbarui riwayat lintasan dan postur via TrackManager ---
        self.track_manager.update_tracks(
            tracked_objects=tracked_objects,
            keypoints_per_track=keypoints_per_track,
            rois=self.rois,
            frame_height=frame_height,
            posture_classifier=self.posture_classifier,
            hand_activity_func=calculate_hand_activity,
            current_frame=self.frame_count
        )

        # --------------------------------------
        # --- IDENTIFY BARBER FOR EACH CHAIR ---
        # --------------------------------------
        for chair_id in range(len(self.rois)):
            barber_tid = self.track_manager.identify_barber_for_chair(
                chair_id, self.rois, tracked_objects
            )
            if barber_tid is not None:
                self.track_manager.person_types[barber_tid] = 'barber'
                # Mark customer (person inside ROI)
                for obj in tracked_objects:
                    if obj.track_id != barber_tid:
                        bbox = obj.xyxy
                        centroid = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
                        if chair_id < len(self.rois):
                            roi = self.rois[chair_id]
                            if (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3]):
                                self.track_manager.person_types[obj.track_id] = 'customer'
        
        # --- Cleanup inactive tracks periodically ---
        self.track_manager.cleanup_counter += 1
        if self.track_manager.cleanup_counter >= self.track_manager.cleanup_interval:
            removed = self.track_manager.cleanup(self.frame_count)
            if removed > 0:
                print(f"[CLEANUP] Removed {removed} inactive tracks")
            self.track_manager.cleanup_counter = 0
        
        # --- Anti-kedipan via ROIManager ---
        stable_status = self.roi_manager.update_occupancy(person_boxes)
        
        # --- Penilaian dan Mesin Status (jika diaktifkan) ---
        session_data = {} if self.use_scoring else None
        if self.use_scoring:
            for chair_id in range(len(self.rois)):
                if stable_status[chair_id]:
                    # Hitung durasi (disederhanakan: gunakan hitungan frame sebagai proksi)
                    duration = self.frame_count  # frame yang diproses
                    
                    # Hitung skor via ScoringEngine
                    # PERBAIKAN BUG: `tracked_objects` diteruskan agar
                    # `identify_barber_for_chair()` dapat bekerja dengan benar.
                    score, breakdown = self.scoring_engine.calculate(
                        chair_id=chair_id,
                        track_manager=self.track_manager,
                        rois=self.rois,
                        duration=duration,
                        tracked_objects=tracked_objects
                    )
                    
                    # Perbarui mesin status
                    # PERBAIKAN BUG: `person_count` sebelumnya hanya menghitung orang
                    # DI DALAM ROI (via `count_persons_in_roi`). Karena barber berdiri
                    # di luar/dekat ROI, person_count selalu 1, sehingga transisi
                    # IDLE → PENDING (butuh person_count >= 2) tidak pernah terjadi.
                    # Sekarang kita hitung: 1 (customer di ROI) + 1 (barber teridentifikasi)
                    person_count = self.roi_manager.count_persons_in_roi(person_boxes, chair_id)
                    barber_tid = self.track_manager.identify_barber_for_chair(
                        chair_id, self.rois, tracked_objects
                    )
                    if barber_tid is not None:
                        person_count += 1  # Tambahkan barber yang berdiri
                    
                    new_state, status_changed, timeout_occurred, trigger_reason = self.state_machine.update(
                        chair_id, score, person_count, duration, breakdown
                    )
                    
                    # Bangun data sesi
                    person_ids = [obj.track_id for obj in tracked_objects if self.roi_manager.check_occupancy(
                        obj.xyxy, self.rois[chair_id]
                    )]
                    
                    session_data[chair_id] = {
                        'is_active': new_state in ('ACTIVE', 'ENDING'),
                        'confidence_score': score,
                        'session_status': new_state,
                        'status_changed': status_changed,
                        'score_breakdown': breakdown,
                        'person_ids': person_ids,
                        'duration_seconds': duration,
                        'person_count': person_count
                    }
        
        # --- LOGGING DETECTION_COMPLETE (sampling berbasis waktu via SmartLogger) ---
        processing_time_ms = (time.time() - start_time) * 1000
        chair_status = {}
        for i, status in enumerate(stable_status):
            chair_status[f"chair_{i+1}"] = "occupied" if status else "empty"
        
        tracked_ids = [obj.track_id for obj in tracked_objects]
        
        smart_logger.log_if_needed(
            component_key="detector",
            event="DETECTION_COMPLETE",
            level="DEBUG",
            total_persons_detected=len(person_boxes),
            tracked_ids=tracked_ids,
            chair_status=chair_status,
            processing_time_ms=round(processing_time_ms, 2)
        )
        
        if self.use_scoring:
            return stable_status, person_boxes, session_data
        else:
            return stable_status, person_boxes, {} 
    
    def draw_ui(self, frame, occupancy_status, person_boxes, session_data=None):
        """Fungsi khusus untuk menggambar kotak di SETIAP frame"""
        # Gambar Bounding Box Orang (Opsional)
        for box in person_boxes:
            cv2.rectangle(frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (255, 100, 0), 1)

        # Gambar ROI Kursi
        for i, is_occupied in enumerate(occupancy_status):
            roi = self.rois[i]
            color = (0, 255, 0) if is_occupied else (0, 0, 255)
            status_text = "TERISI" if is_occupied else "KOSONG"
            
            # Add scoring info if available
            if session_data and i in session_data:
                sd = session_data[i]
                score_text = f"Score: {sd['confidence_score']} | {sd['session_status']}"
                cv2.putText(frame, score_text, (roi[0], roi[1] - 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.rectangle(frame, (roi[0], roi[1]), (roi[2], roi[3]), color, 2)
            cv2.putText(frame, f"Kursi {i+1}: {status_text}", (roi[0], roi[1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        return frame