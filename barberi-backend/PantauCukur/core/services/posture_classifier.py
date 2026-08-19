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
    def __init__(self):
        load_dotenv()
        self.keypoint_conf_threshold = float(os.environ.get('KEYPOINT_CONF_THRESHOLD', '0.3'))
        self.sitting_area_ratio_threshold = float(os.environ.get('SITTING_AREA_RATIO_THRESHOLD', '0.55'))
        self.sitting_temporal_window = int(os.environ.get('SITTING_TEMPORAL_WINDOW', '10'))
        self.sitting_min_consistent_frames = int(os.environ.get('SITTING_MIN_CONSISTENT_FRAMES', '5'))
        self.chair_detection_confidence = float(os.environ.get('CHAIR_DETECTION_CONFIDENCE', '0.3'))
        self._posture_history = {}
        
        # ============================================================
        # PERBAIKAN BUG POSTURE: Membedakan SITTING vs STANDING lebih akurat
        # ============================================================
        # MASALAH: Hampir semua track diklasifikasikan STANDING (259/269 = 96.3%)
        # karena butuh 2 votes (area_ratio > 0.55 DAN vertical_diff < 0.15).
        # Orang duduk dengan cape melebar punya area_ratio TINGGI (> 0.55) TAPI
        # vertical_diff SERING > 0.15 karena cape membuat hip_y terlihat lebih
        # rendah dari sebenarnya. Akibatnya hanya 1 vote → STANDING.
        #
        # SOLUSI:
        # 1. Turunkan threshold vertical_diff dari 0.15 ke 0.20 (cape besar)
        # 2. Vertical_diff dihitung relatif terhadap TINGGI BBOX (bukan frame),
        #    sehingga proporsional terhadap ukuran orang di frame.
        # 3. Jika area_ratio > 0.55 DAN vertical_diff tidak tersedia (keypoints
        #    shoulder/hip tidak reliable), anggap SITTING karena area_ratio
        #    tinggi mengindikasikan cape melebar (customer duduk).
        # 4. Jika area_ratio > 0.55 TAPI vertical_diff >= 0.20, tetap STANDING
        #    karena ini adalah barber yang sedang membungkuk mencukur.
        self.sitting_vertical_diff_threshold = float(os.environ.get('SITTING_VERTICAL_DIFF_THRESHOLD', '0.20'))
    
    def classify(self, kpts, bbox=None, roi=None, frame_height=None, chair_id=None, track_id=None):
        keypoints_reliable = self._has_reliable_keypoints(kpts)
        is_inside_roi = self._is_inside_roi(roi, bbox)
        
        votes = 0
        signals_used = []
        ratio = None
        shoulder_y = None
        hip_y = None
        signal_source = None
        
        # === PRIORITAS 1: Customer dengan cape ===
        # Di dalam ROI + body keypoints tidak reliable → SITTING
        if is_inside_roi and not keypoints_reliable:
            result = 'SITTING'
            signals_used.append('location_in_roi_no_keypoints')
            signal_source = 'location_fallback'
        
        # === PRIORITAS 2: Keypoints body reliable ===
        elif keypoints_reliable:
            signal_source = 'keypoints'
            vertical_diff = None
            has_shoulder_hip = False
            
            # Signal 1: Area ratio
            if bbox is not None:
                ratio = self._calculate_area_ratio(bbox)
                if ratio > self.sitting_area_ratio_threshold:
                    votes += 1
                    signals_used.append('area_ratio')
            
            # Signal 2: Shoulder-hip distance
            try:
                if (kpts[LEFT_SHOULDER][2] >= self.keypoint_conf_threshold and
                    kpts[RIGHT_SHOULDER][2] >= self.keypoint_conf_threshold and
                    kpts[LEFT_HIP][2] >= self.keypoint_conf_threshold and
                    kpts[RIGHT_HIP][2] >= self.keypoint_conf_threshold):
                    
                    has_shoulder_hip = True
                    shoulder_y = (kpts[LEFT_SHOULDER][1] + kpts[RIGHT_SHOULDER][1]) / 2
                    hip_y = (kpts[LEFT_HIP][1] + kpts[RIGHT_HIP][1]) / 2
                    
                    # PERBAIKAN: Hitung vertical_diff relatif terhadap TINGGI BBOX
                    # (bukan frame_height). Ini membuat proporsional terhadap ukuran
                    # orang di frame. Threshold dilonggarkan ke 0.20 karena cape
                    # membuat hip_y terlihat lebih rendah.
                    if bbox is not None:
                        bbox_height = bbox[3] - bbox[1]
                        vertical_diff = (hip_y - shoulder_y) / bbox_height if bbox_height > 0 else (hip_y - shoulder_y) / frame_height
                    elif frame_height and frame_height > 0:
                        vertical_diff = (hip_y - shoulder_y) / frame_height
                    else:
                        vertical_diff = hip_y - shoulder_y
                    
                    if vertical_diff < self.sitting_vertical_diff_threshold:
                        votes += 1
                        signals_used.append('shoulder_hip_distance')
            except Exception:
                pass
            
            # ============================================================
            # PERBAIKAN LOGIKA KLASIFIKASI (berdasarkan analisis log):
            # 
            # Dari log POSTURE_CLASSIFIED:
            # - Barber membungkuk mencukur: area_ratio=0.56-0.85, 
            #   vertical_diff=0.21-0.35 (frame-based) → STANDING
            # - Customer duduk dengan cape: area_ratio > 0.55, 
            #   vertical_diff KECIL karena cape membuat hip_y dekat shoulder_y
            #   → SITTING
            # 
            # Aturan baru:
            # 1. area_ratio > 0.55 DAN vertical_diff < 0.20 → SITTING (2 votes)
            # 2. area_ratio > 0.55 DAN vertical_diff TIDAK tersedia (keypoints
            #    shoulder/hip tidak reliable) → SITTING (area_ratio saja cukup,
            #    karena cape menutupi body keypoints)
            # 3. area_ratio > 0.55 TAPI vertical_diff >= 0.20 → STANDING
            #    (barber membungkuk, bukan customer duduk)
            # 4. vertical_diff < 0.20 saja (tanpa area_ratio) → SITTING
            #    (orang duduk tegak tanpa cape melebar)
            # ============================================================
            if 'area_ratio' in signals_used:
                if has_shoulder_hip:
                    # Ada data vertical_diff → gunakan kombinasi
                    result = 'SITTING' if vertical_diff < self.sitting_vertical_diff_threshold else 'STANDING'
                else:
                    # Tidak ada data vertical_diff → area_ratio saja cukup
                    result = 'SITTING'
            elif 'shoulder_hip_distance' in signals_used:
                # Hanya vertical_diff yang terpenuhi → SITTING
                result = 'SITTING'
            else:
                result = 'STANDING'
        
        # === PRIORITAS 3: Fallback ===
        else:
            result = 'STANDING'
            signals_used.append('location_outside_roi')
            signal_source = 'location_fallback'
        
        # === TEMPORAL CONSISTENCY ===
        result = self._apply_temporal_consistency(track_id, result)
        
        # === LOGGING ===
        smart_logger.log_if_needed(
            component_key="posture",
            event="POSTURE_CLASSIFIED",
            level="INFO",
            chair_id=chair_id,
            track_id=track_id,
            posture=result,
            signals_used=signals_used,
            vote_result=votes,
            area_ratio=ratio,
            shoulder_y=shoulder_y,
            hip_y=hip_y,
            keypoints_reliable=keypoints_reliable,
            signal_source=signal_source,
            is_inside_roi=is_inside_roi,
            bbox=bbox,
            roi=roi
        )
        
        return result
    
    def _has_reliable_keypoints(self, kpts):
        """HANYA hitung keypoints BODY (bahu & pinggul). 
        Elbow/wrist TIDAK dihitung karena bisa terdeteksi meskipun cape menutupi tubuh."""
        if kpts is None or len(kpts) < 13:
            return False
        
        # HANYA bahu dan pinggul yang BERMAKNA untuk membedakan duduk vs berdiri
        body_indices = [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP]
        
        reliable_count = sum(
            1 for idx in body_indices
            if idx < len(kpts) and kpts[idx][2] >= self.keypoint_conf_threshold
        )
        
        # Butuh minimal 2 dari 4 keypoints body
        return reliable_count >= 2
    
    def _is_inside_roi(self, roi, bbox):
        """Cek overlap bbox dengan ROI (bukan centroid)."""
        if roi is None or bbox is None:
            return False
        
        x1 = max(roi[0], bbox[0])
        y1 = max(roi[1], bbox[1])
        x2 = min(roi[2], bbox[2])
        y2 = min(roi[3], bbox[3])
        
        if x2 <= x1 or y2 <= y1:
            return False
        
        intersection = (x2 - x1) * (y2 - y1)
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        
        # Jika > 30% bbox overlap dengan ROI → anggap di dalam
        return (intersection / bbox_area) > 0.3 if bbox_area > 0 else False
    
    def _apply_temporal_consistency(self, track_id, result):
        if track_id is None:
            return result
        
        history = self._posture_history.setdefault(track_id, [])
        history.append(result)
        
        if len(history) > self.sitting_temporal_window:
            history.pop(0)
        
        if len(history) < self.sitting_min_consistent_frames:
            return result
        
        sitting_count = sum(1 for p in history if p == 'SITTING')
        standing_count = len(history) - sitting_count
        
        return 'SITTING' if sitting_count > standing_count else 'STANDING'
    
    def _calculate_area_ratio(self, bbox):
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width / height if height > 0 else 0