# C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\track_manager.py
import os
import numpy as np
from dotenv import load_dotenv
from logger import smart_logger

class TrackManager:
    """Tracking data management logic."""
    
    def __init__(self):
        load_dotenv()
        self.trajectories = {}
        self.posture_history = {}
        self.hand_activity = {}
        self._prev_keypoints = {}
        self.track_last_seen = {}
        self.track_timeout = int(os.environ.get('TRACK_TIMEOUT_SECONDS', '60')) * 30
        self.cleanup_counter = 0
        self.cleanup_interval = int(os.environ.get('CLEANUP_INTERVAL_FRAMES', '300'))
        self.person_types = {}
    
    def update_tracks(self, tracked_objects, keypoints_per_track, rois, frame_height, posture_classifier, hand_activity_func, current_frame=None):
        if current_frame is None:
            current_frame = 0
        
        active_track_ids = set()
        
        for obj in tracked_objects:
            track_id = obj.track_id
            active_track_ids.add(track_id)
            bbox = obj.xyxy
            centroid = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
            
            if track_id not in self.trajectories:
                self.trajectories[track_id] = []
            self.trajectories[track_id].append(centroid)
            
            self.track_last_seen[track_id] = current_frame
            
            kpts = keypoints_per_track.get(track_id)
            
            if kpts is not None:
                chair_roi = None
                chair_id = None
                for i, roi in enumerate(rois):
                    if (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3]):
                        chair_roi = roi
                        chair_id = i
                        break
                
                # PERBAIKAN BUG: Jika orang tidak berada di dalam ROI (barber berdiri
                # di dekat kursi), tentukan chair_id berdasarkan jarak terdekat ke
                # pusat ROI. Ini penting agar `calculate_hand_activity` dapat
                # mengidentifikasi barber dengan benar.
                if chair_id is None and rois:
                    min_dist = float('inf')
                    for i, roi in enumerate(rois):
                        roi_center = ((roi[0] + roi[2]) / 2, (roi[1] + roi[3]) / 2)
                        dist = np.sqrt((centroid[0] - roi_center[0])**2 + (centroid[1] - roi_center[1])**2)
                        if dist < min_dist:
                            min_dist = dist
                            chair_id = i
                            chair_roi = rois[i]
                
                posture = posture_classifier.classify(
                    kpts=kpts,
                    bbox=bbox,
                    roi=chair_roi,
                    frame_height=frame_height,
                    chair_id=chair_id,
                    track_id=track_id
                )
                if track_id not in self.posture_history:
                    self.posture_history[track_id] = []
                self.posture_history[track_id].append(posture)
                
                prev_kpts = self._prev_keypoints.get(track_id)
                
                # PERBAIKAN BUG: `chair_id` sekarang diteruskan (sebelumnya None),
                # sehingga `is_barber_for_chair()` di hand_activity.py dapat bekerja
                # dan poin hand activity untuk barber dapat dihitung.
                hand_points = hand_activity_func(
                    kpts, 
                    prev_kpts, 
                    frame_height,
                    chair_id=chair_id,
                    rois=rois,
                    posture_history=self.posture_history,
                    tracked_objects=tracked_objects,
                    track_id=track_id
                )
                if track_id not in self.hand_activity:
                    self.hand_activity[track_id] = []
                self.hand_activity[track_id].append(hand_points)
                
                self._prev_keypoints[track_id] = kpts
        
        # Logging TRACK_UPDATE (sampling berbasis waktu via SmartLogger)
        tracked_persons_count = len(active_track_ids)
        active_tracks_count = len(self.trajectories)
        smart_logger.log_if_needed(
            component_key="track_manager",
            event="TRACK_UPDATE",
            level="DEBUG",
            tracked_persons_count=tracked_persons_count,
            active_tracks_count=active_tracks_count,
            track_ids=list(active_track_ids)
        )
    
    def identify_barber_for_chair(self, chair_id, rois, tracked_objects):
        """Identify which track_id is the barber for a given chair.
        
        PERBAIKAN BUG: Sebelumnya, logika melewati (skip) siapa pun yang berada
        di dalam ROI (`is_inside_roi → continue`). Ini salah karena barber berdiri
        DI DALAM atau SANGAT DEKAT dengan ROI kursi.
        
        Strategi baru:
        1. Barber diidentifikasi berdasarkan POSTUR (STANDING), bukan lokasi
        2. Customer diidentifikasi berdasarkan postur (SITTING) di dalam ROI
        3. Threshold jarak dilonggarkan (300px) karena ROI sengaja dibuat kecil
        4. Gunakan mayoritas postur dari 10 frame terakhir (bukan hanya frame terakhir)
           untuk mengurangi fluktuasi klasifikasi postur
        
        Returns:
            int or None: track_id of barber, or None if not found
        """
        if chair_id >= len(rois):
            return None
        
        chair_roi = rois[chair_id]
        chair_center = ((chair_roi[0] + chair_roi[2]) / 2, (chair_roi[1] + chair_roi[3]) / 2)
        
        barber_candidates = []
        
        for obj in tracked_objects:
            track_id = obj.track_id
            bbox = obj.xyxy
            centroid = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
            
            # Dapatkan postur dari riwayat (mayoritas dari 10 frame terakhir)
            # Ini lebih stabil daripada hanya frame terakhir yang bisa berfluktuasi
            posture = None
            if track_id in self.posture_history and self.posture_history[track_id]:
                recent = self.posture_history[track_id][-10:]
                if recent:
                    standing_count = sum(1 for p in recent if p == 'STANDING')
                    sitting_count = len(recent) - standing_count
                    posture = 'STANDING' if standing_count > sitting_count else 'SITTING'
            
            # Jarak ke pusat kursi (dihitung sebelum logging)
            distance = np.sqrt((centroid[0] - chair_center[0])**2 + (centroid[1] - chair_center[1])**2)
            
            # Logging diagnostik: tampilkan postur & jarak untuk setiap kandidat
            smart_logger.log_if_needed(
                component_key="track_manager",
                event="BARBER_CANDIDATE_CHECK",
                level="DEBUG",
                chair_id=chair_id,
                track_id=track_id,
                centroid=[round(c, 1) for c in centroid],
                posture=posture,
                distance_to_chair=round(distance, 1)
            )
            
            # Barber harus berdiri. Jika postur belum diketahui (None) pada frame
            # awal, tetap pertimbangkan sebagai kandidat (fallback untuk cold start).
            if posture == 'SITTING':
                continue  # Customer yang duduk, bukan barber
            
            # Longgarkan threshold jarak: barber bisa berdiri di dalam ROI
            # atau sangat dekat dengannya (ROI sengaja dibuat kecil/kencang)
            if distance > 300:
                continue
            
            barber_candidates.append((track_id, distance))
        
        if not barber_candidates:
            return None
        
        # Kembalikan orang berdiri terdekat ke kursi
        barber_candidates.sort(key=lambda x: x[1])
        return barber_candidates[0][0]
    
    def get_person_type(self, track_id):
        """Return 'barber', 'customer', or 'unknown'."""
        return self.person_types.get(track_id, 'unknown')
    
    def cleanup(self, current_frame):
        """Remove track data that hasn't been seen for > timeout frames."""
        to_remove = []
        
        for track_id, last_seen in self.track_last_seen.items():
            if current_frame - last_seen > self.track_timeout:
                to_remove.append(track_id)
        
        for track_id in to_remove:
            # Remove from all dictionaries
            self.trajectories.pop(track_id, None)
            self.posture_history.pop(track_id, None)
            self.hand_activity.pop(track_id, None)
            self._prev_keypoints.pop(track_id, None)
            self.track_last_seen.pop(track_id, None)
            self.person_types.pop(track_id, None)
        
        return len(to_remove)
    
    def get_trajectory(self, track_id):
        return self.trajectories.get(track_id, [])
    
    def get_posture_history(self, track_id):
        return self.posture_history.get(track_id, [])
    
    def get_hand_activity(self, track_id):
        return self.hand_activity.get(track_id, [])
