import os
import numpy as np
from dotenv import load_dotenv

# COCO keypoint indices for YOLO-Pose
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
    """Posture classification logic using multiple signals."""
    
    def __init__(self):
        load_dotenv()
        self.keypoint_conf_threshold = float(os.environ.get('KEYPOINT_CONF_THRESHOLD', '0.3'))
        self.sitting_area_ratio_threshold = float(os.environ.get('SITTING_AREA_RATIO_THRESHOLD', '0.55'))
        self.sitting_temporal_window = int(os.environ.get('SITTING_TEMPORAL_WINDOW', '10'))
        self.sitting_min_consistent_frames = int(os.environ.get('SITTING_MIN_CONSISTENT_FRAMES', '5'))
        self.chair_detection_confidence = float(os.environ.get('CHAIR_DETECTION_CONFIDENCE', '0.3'))
    
    def classify(self, kpts, bbox=None, roi=None, frame_height=None):
        """Mengklasifikasikan seseorang sebagai DUDUK atau BERDIRI berdasarkan beberapa sinyal.

            Argumen:
            kpts: array numpy dengan bentuk (17, 3) di mana setiap baris adalah [x, y, kepercayaan]
            bbox: bounding box [x1, y1, x2, y2] untuk area ratio
            roi: region of interest [x1, y1, x2, y2] untuk deteksi kursi
            frame_height: tinggi frame untuk normalisasi (opsional)
            Mengembalikan:
            str: 'SITTING' atau 'STANDING'
        
        """
        if kpts is None or len(kpts) < 13:
            return 'STANDING'
    
        votes = 0  # votes for SITTING
        
        # Signal 1: Area ratio method
        if bbox is not None:
            ratio = self._calculate_area_ratio(bbox)
            if ratio > self.sitting_area_ratio_threshold:
                votes += 1
        
        # Signal 2: Temporal consistency (requires track_id)
        # We'll handle this outside by passing track_id via _get_consistent_posture
        # For now, we rely on the caller to provide track_id via a separate mechanism
        
        # Signal 3: Keypoint-based shoulder-hip distance (existing logic)
        try:
            if (kpts[LEFT_SHOULDER][2] < self.keypoint_conf_threshold or
                kpts[RIGHT_SHOULDER][2] < self.keypoint_conf_threshold or
                kpts[LEFT_HIP][2] < self.keypoint_conf_threshold or
                kpts[RIGHT_HIP][2] < self.keypoint_conf_threshold):
                # If keypoints unreliable, rely on area ratio only
                if votes >= 1:
                    return 'SITTING'
                return 'STANDING'
            
            shoulder_y = (kpts[LEFT_SHOULDER][1] + kpts[RIGHT_SHOULDER][1]) / 2
            hip_y = (kpts[LEFT_HIP][1] + kpts[RIGHT_HIP][1]) / 2
            
            if frame_height and frame_height > 0:
                vertical_diff = (hip_y - shoulder_y) / frame_height
            else:
                vertical_diff = hip_y - shoulder_y
            
            if vertical_diff < 0.15:
                votes += 1
        except Exception:
            pass
        
        # Decision: return SITTING if votes >= 2
        if votes >= 2:
            return 'SITTING'
        else:
            return 'STANDING'
    
    def _calculate_area_ratio(self, bbox):
        """Calculate width/height ratio of person bounding box."""
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width / height if height > 0 else 0
    
    def _get_consistent_posture(self, posture_history, track_id):
        """Get posture that has been consistent across last N frames."""
        if track_id not in posture_history:
            return None
        recent = posture_history[track_id][-self.sitting_temporal_window:]
        if len(recent) < self.sitting_min_consistent_frames:
            return None
        sitting_count = sum(1 for p in recent if p == 'SITTING')
        standing_count = len(recent) - sitting_count
        if sitting_count > standing_count * 2:
            return 'SITTING'
        elif standing_count > sitting_count * 2:
            return 'STANDING'
        return None
