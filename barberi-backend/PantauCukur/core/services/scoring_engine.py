# C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\scoring_engine.py
import os
import numpy as np
from dotenv import load_dotenv
from logger import smart_logger

class ScoringEngine:
    """Scoring calculation logic for session evaluation."""

    def __init__(self):
        load_dotenv()
        self.hand_activity_weight = float(os.environ.get('HAND_ACTIVITY_WEIGHT', '0.35'))
        self.posture_weight = float(os.environ.get('POSTURE_WEIGHT', '0.20'))
        self.temporal_weight = float(os.environ.get('TEMPORAL_WEIGHT', '0.25'))
        self.person_count_weight = float(os.environ.get('PERSON_COUNT_WEIGHT', '0.20'))
        self._last_score = None

    def calculate(self, chair_id, track_manager, rois, duration, tracked_objects=None):
        """Hitung skor sesi keseluruhan untuk suatu kursi.
        
        PERBAIKAN BUG: Parameter `tracked_objects` ditambahkan agar
        `calculate_hand_score()` dapat mengidentifikasi barber dengan benar.
        Sebelumnya, `tracked_objects` tidak diteruskan sehingga selalu [] 
        dan `identify_barber_for_chair()` selalu mengembalikan None.
        """
        # 1. Posture Score (20%)
        posture_score = self.calculate_posture_score(chair_id, track_manager, rois, tracked_objects)

        # 2. Hand Activity Score (35%)
        hand_score = self.calculate_hand_score(chair_id, track_manager, rois, tracked_objects)

        # 3. Temporal Score (25%)
        temporal_score = self.calculate_temporal_score(duration)

        # 4. Person Count Score (20%)
        person_count_score = self.calculate_person_count_score(chair_id, track_manager, rois, tracked_objects)

        # Weighted sum
        total_score = (
            posture_score * self.posture_weight +
            hand_score * self.hand_activity_weight +
            temporal_score * self.temporal_weight +
            person_count_score * self.person_count_weight
        )

        total_score_int = int(total_score)

        # Logging: sampling berbasis waktu via SmartLogger
        # Log selalu jika skor berubah signifikan (delta > 20 poin)
        force_log = (
            self._last_score is not None and
            abs(total_score_int - self._last_score) > 20
        )

        # Logging diagnostik: komponen skor individual sebelum agregasi
        smart_logger.log_if_needed(
            component_key="scoring",
            event="SCORE_CALCULATED",
            level="INFO",
            force=force_log,
            chair_id=chair_id,
            total_score=total_score_int,
            breakdown={
                'posture': posture_score,
                'hand_activity': hand_score,
                'temporal': temporal_score,
                'person_count': person_count_score
            },
            weights_used={
                'hand_activity': self.hand_activity_weight,
                'posture': self.posture_weight,
                'temporal': self.temporal_weight,
                'person_count': self.person_count_weight
            },
            person_count=len(track_manager.trajectories) if track_manager else 0,
            duration_seconds=duration
        )

        self._last_score = total_score_int

        return total_score_int, {
            'posture': posture_score,
            'hand_activity': hand_score,
            'temporal': temporal_score,
            'person_count': person_count_score
        }
    
    def calculate_posture_score(self, chair_id, track_manager, rois, tracked_objects=None):
        """Posture score berdasarkan jumlah orang STANDING di area kursi.
        
        LOGIKA SEDERHANA:
        - Barber SELALU STANDING (terdeteksi oleh YOLO-Pose)
        - Customer dengan cape TIDAK STANDING (body keypoints tidak terdeteksi)
        - Jika ada 2 orang di area kursi dan TEPAT 1 yang STANDING → score 100
        - Jika 0 atau 2 orang STANDING → score 0 (bukan sesi cukur)
        - Jika kurang dari 2 orang → score 0
        
        PERBAIKAN BUG (2026-08-18):
        - Logging diubah dari DEBUG ke INFO agar SELALU muncul di log
          (sebelumnya diblokir oleh LOG_LEVEL_MINIMAL=INFO)
        - Menambahkan detail per-track (posture, centroid, jarak ke ROI)
        - Filter track yang terlalu jauh dari ROI (bukan customer kursi ini)
        """
        # ============================================================
        # LANGKAH 1: Kumpulkan semua track yang terkait dengan kursi ini
        # ============================================================
        track_ids_in_chair = []
        track_details = []  # Untuk logging detail per track
        
        if chair_id < len(rois):
            roi = rois[chair_id]
            roi_center = ((roi[0] + roi[2]) / 2, (roi[1] + roi[3]) / 2)
            
            # 1a. Tambahkan barber (berdiri dekat/ di dalam ROI)
            barber_tid = track_manager.identify_barber_for_chair(chair_id, rois, tracked_objects or [])
            if barber_tid is not None:
                track_ids_in_chair.append(barber_tid)
                track_details.append({
                    'track_id': barber_tid,
                    'role': 'barber',
                    'posture': track_manager.get_posture_history(barber_tid)[-1] if track_manager.get_posture_history(barber_tid) else None
                })
            
            # 1b. Tambahkan orang yang berada DI DALAM ROI (customer)
            for tid, traj in track_manager.trajectories.items():
                if tid == barber_tid:
                    continue  # Jangan duplikat barber
                if traj:
                    centroid = traj[-1]
                    # PERBAIKAN: Hitung jarak centroid ke pusat ROI
                    distance_to_roi_center = np.sqrt(
                        (centroid[0] - roi_center[0])**2 + 
                        (centroid[1] - roi_center[1])**2
                    )
                    
                    # PERBAIKAN: Hanya anggap sebagai customer jika centroid
                    # benar-benar DI DALAM ROI (bukan hanya lewat di dekatnya)
                    is_inside = (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3])
                    
                    if is_inside:
                        # ============================================================
                        # PERBAIKAN BUG: Filter track yang STANDING di dalam ROI.
                        # 
                        # MASALAH: Barber yang berdiri DI DALAM ROI juga masuk ke
                        # `track_ids_in_chair` sebagai "customer" karena centroid-nya
                        # di dalam ROI. Ini menyebabkan `total_people_in_chair` menjadi
                        # 3-6 orang (avg=3.66 dari log) padahal seharusnya hanya 2
                        # (barber + customer duduk).
                        # 
                        # SOLUSI: Hanya anggap sebagai customer jika posture-nya
                        # SITTING. Track yang STANDING di dalam ROI adalah barber
                        # atau orang lain yang berdiri, bukan customer duduk.
                        # ============================================================
                        posture = None
                        if tid in track_manager.posture_history and track_manager.posture_history[tid]:
                            recent = track_manager.posture_history[tid][-10:]
                            if recent:
                                standing = sum(1 for p in recent if p == 'STANDING')
                                posture = 'STANDING' if (standing / len(recent)) > 0.5 else 'SITTING'
                        
                        # Skip track yang STANDING di dalam ROI (bukan customer)
                        if posture == 'STANDING':
                            track_details.append({
                                'track_id': tid,
                                'role': 'ignored_standing_in_roi',
                                'posture': posture,
                                'centroid': [round(c, 1) for c in centroid],
                                'distance_to_roi_center': round(distance_to_roi_center, 1)
                            })
                            continue
                        
                        track_ids_in_chair.append(tid)
                        track_details.append({
                            'track_id': tid,
                            'role': 'customer',
                            'posture': posture,
                            'centroid': [round(c, 1) for c in centroid],
                            'distance_to_roi_center': round(distance_to_roi_center, 1)
                        })
        
        total_people = len(track_ids_in_chair)
        
        # ============================================================
        # LANGKAH 2: Hitung berapa yang STANDING
        # ============================================================
        standing_count = 0
        standing_details = []
        for tid in track_ids_in_chair:
            if tid in track_manager.posture_history:
                recent = track_manager.posture_history[tid][-10:]
                if recent:
                    standing = sum(1 for p in recent if p == 'STANDING')
                    ratio = standing / len(recent)
                    # Anggap STANDING jika mayoritas 10 frame terakhir
                    if ratio > 0.5:
                        standing_count += 1
                        standing_details.append({
                            'track_id': tid,
                            'standing_ratio': round(ratio, 2),
                            'recent_postures': recent[-5:]
                        })
        
        # ============================================================
        # LANGKAH 3: Logging diagnostik (INFO agar selalu muncul)
        # ============================================================
        if total_people >= 2 and standing_count == 1:
            reason = "exactly_one_standing"
        elif total_people < 2:
            reason = "too_few_people"
        elif standing_count == 0:
            reason = "no_standing"
        else:
            reason = "too_many_standing"
        
        smart_logger.log_if_needed(
            component_key="scoring",
            event="POSTURE_SCORE_DEBUG",
            level="INFO",  # PERBAIKAN: INFO agar selalu muncul di log
            chair_id=chair_id,
            total_people_in_chair=total_people,
            standing_count=standing_count,
            track_ids_in_chair=track_ids_in_chair,
            barber_tid=barber_tid if chair_id < len(rois) else None,
            reason=reason,
            track_details=track_details,
            standing_details=standing_details,
            roi=rois[chair_id] if chair_id < len(rois) else None
        )
        
        # ============================================================
        # LANGKAH 4: Decision
        # ============================================================
        # Posture score = 100 HANYA jika:
        # - Ada >= 2 orang di area kursi
        # - TEPAT 1 orang yang STANDING (barber)
        # - Sisanya TIDAK standing (customer dengan cape)
        if total_people >= 2 and standing_count == 1:
            return 100
        
        return 0
    
    def calculate_hand_score(self, chair_id, track_manager, rois, tracked_objects=None):
        """Calculate hand activity score (0-100) based on barber's hand activity only.
        
        PERBAIKAN BUG: `tracked_objects` sekarang diteruskan dari `calculate()`
        sehingga `identify_barber_for_chair()` dapat bekerja dengan benar.
        """
        # Identify barber for this chair
        barber_track_id = track_manager.identify_barber_for_chair(chair_id, rois, tracked_objects or [])
        
        # Logging diagnostik
        smart_logger.log_if_needed(
            component_key="scoring",
            event="HAND_SCORE_DEBUG",
            level="DEBUG",
            chair_id=chair_id,
            barber_track_id=barber_track_id,
            tracked_objects_count=len(tracked_objects or [])
        )
        
        if barber_track_id is None:
            # Fallback: gunakan semua orang di dalam ROI (perilaku lama)
            total_points = 0
            total_frames = 0
            
            for tid, points_list in track_manager.hand_activity.items():
                if tid in track_manager.trajectories and track_manager.trajectories[tid]:
                    centroid = track_manager.trajectories[tid][-1]
                    if chair_id < len(rois):
                        roi = rois[chair_id]
                        if (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3]):
                            total_points += sum(points_list)
                            total_frames += len(points_list)
            
            if total_frames == 0:
                return 0
            
            max_possible = total_frames * 5
            score = (total_points / max_possible) * 100 if max_possible > 0 else 0
            return min(int(score), 100)
        
        # Gunakan hanya aktivitas tangan barber
        points_list = track_manager.hand_activity.get(barber_track_id, [])
        if not points_list:
            return 0
        
        total_points = sum(points_list)
        total_frames = len(points_list)
        
        if total_frames == 0:
            return 0
        
        max_possible = total_frames * 5
        score = (total_points / max_possible) * 100 if max_possible > 0 else 0
        return min(int(score), 100)
    
    def calculate_temporal_score(self, duration):
        """Calculate temporal score based on session duration."""
        if duration < 180:  # 3 minutes
            return 0
        elif duration < 300:  # 3-5 minutes
            return 40
        elif duration < 600:  # 5-10 minutes
            return 70
        else:  # > 10 minutes
            return 100
    
    def calculate_person_count_score(self, chair_id, track_manager, rois, tracked_objects=None):
        """Calculate person count score based on how often 2 persons are present.
        
        PERBAIKAN BUG: Sebelumnya, hanya menghitung orang DI DALAM ROI.
        Sekarang kita juga menyertakan barber yang berdiri dekat/ di dalam ROI
        sehingga total 2 orang (barber + customer) dapat terdeteksi.
        """
        # Identifikasi barber untuk kursi ini
        barber_tid = None
        if tracked_objects is not None:
            barber_tid = track_manager.identify_barber_for_chair(chair_id, rois, tracked_objects)
        
        # Kumpulkan track yang terkait dengan kursi ini
        track_ids_in_chair = []
        
        # 1. Tambahkan barber jika teridentifikasi
        if barber_tid is not None:
            track_ids_in_chair.append(barber_tid)
        
        # 2. Tambahkan orang di dalam ROI (customer)
        for tid, traj in track_manager.trajectories.items():
            if tid == barber_tid:
                continue
            if traj:
                centroid = traj[-1]
                if chair_id < len(rois):
                    roi = rois[chair_id]
                    if (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3]):
                        track_ids_in_chair.append(tid)
        
        # Logging diagnostik
        smart_logger.log_if_needed(
            component_key="scoring",
            event="PERSON_COUNT_DEBUG",
            level="DEBUG",
            chair_id=chair_id,
            barber_track_id=barber_tid,
            track_ids_in_chair=track_ids_in_chair
        )
        
        # Estimate based on trajectory lengths
        if not track_ids_in_chair:
            return 0
        
        # Simple heuristic: if we have at least 2 track_ids, assume 2 persons present
        # More accurate would require per-frame tracking
        if len(track_ids_in_chair) >= 2:
            # Assume 2 persons present for most of the time
            return 100
        else:
            return 0
