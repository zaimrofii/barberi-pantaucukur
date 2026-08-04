        # detector.py
import cv2
import os
import numpy as np
from ultralytics import YOLO
from boxmot import ByteTrack
from dotenv import load_dotenv

from .state_machine import StateMachine
from .scoring_engine import ScoringEngine
from .posture_classifier import PostureClassifier
from .hand_activity import calculate_hand_activity
from .track_manager import TrackManager
from .roi_manager import ROIManager
from .utils import match_keypoints_to_tracked


class BarberDetector:
    def __init__(self, model_path='yolov8n-pose.pt', rois=None):
        print("Sistem AI: Memuat model...")
        self.model = YOLO(model_path)
        self.conf_threshold = 0.5
        self.tracker = ByteTrack()
        
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
        
        print("Sistem AI: Model siap dengan YOLO-Pose, ByteTrack, dan Scoring Engine.")
    
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
        
        # --- Identify barber for each chair ---
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
                    score, breakdown = self.scoring_engine.calculate(
                        chair_id=chair_id,
                        track_manager=self.track_manager,
                        rois=self.rois,
                        duration=duration
                    )
                    
                    # Perbarui mesin status
                    person_count = self.roi_manager.count_persons_in_roi(person_boxes, chair_id)
                    new_state, status_changed = self.state_machine.update(
                        chair_id, score, person_count, duration
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
        
        if self.use_scoring:
            return stable_status, person_boxes, session_data
        else:
            return stable_status, person_boxes
    
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
