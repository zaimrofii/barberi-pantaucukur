import os
import numpy as np
from dotenv import load_dotenv

class TrackManager:
    """Tracking data management logic."""
    
    def __init__(self):
        load_dotenv()
        self.trajectories = {}  # track_id -> list of centroids
        self.posture_history = {}  # track_id -> list of postures
        self.hand_activity = {}  # track_id -> accumulated hand points
        self._prev_keypoints = {}  # track_id -> keypoints array
        self.track_last_seen = {}  # track_id -> last frame seen
        self.track_timeout = int(os.environ.get('TRACK_TIMEOUT_SECONDS', '60')) * 30  # 60 seconds * 30 fps
        self.cleanup_counter = 0
        self.cleanup_interval = int(os.environ.get('CLEANUP_INTERVAL_FRAMES', '300'))
        self.person_types = {}  # track_id -> 'barber', 'customer', or 'unknown'
    
    def update_tracks(self, tracked_objects, keypoints_per_track, rois, frame_height, posture_classifier, hand_activity_func, current_frame=None):
        """Update all track data when new frames arrive."""
        if current_frame is None:
            current_frame = 0
        for obj in tracked_objects:
            track_id = obj.track_id
            bbox = obj.xyxy  # [x1, y1, x2, y2]
            centroid = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
            
            # Perbarui lintasan
            if track_id not in self.trajectories:
                self.trajectories[track_id] = []
            self.trajectories[track_id].append(centroid)
            
            # Update last seen frame
            self.track_last_seen[track_id] = current_frame
            
            # Ambil keypoints untuk track spesifik ini
            kpts = keypoints_per_track.get(track_id)
            
            if kpts is not None:
                # Determine which ROI this track belongs to (for chair detection)
                chair_roi = None
                for i, roi in enumerate(rois):
                    if (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3]):
                        chair_roi = roi
                        break
                
                # Klasifikasikan postur dengan parameter baru
                posture = posture_classifier.classify(
                    kpts=kpts,
                    bbox=bbox,
                    roi=chair_roi,
                    frame_height=frame_height
                )
                if track_id not in self.posture_history:
                    self.posture_history[track_id] = []
                self.posture_history[track_id].append(posture)
                
                # Ambil keypoints sebelumnya untuk perhitungan kecepatan
                prev_kpts = self._prev_keypoints.get(track_id)
                
                # Hitung aktivitas tangan (dengan parameter barber filtering)
                hand_points = hand_activity_func(
                    kpts, 
                    prev_kpts, 
                    frame_height,
                    chair_id=None,  # Will be set per chair in scoring_engine
                    rois=rois,
                    posture_history=self.posture_history,
                    tracked_objects=tracked_objects,
                    track_id=track_id
                )
                if track_id not in self.hand_activity:
                    self.hand_activity[track_id] = []
                self.hand_activity[track_id].append(hand_points)
                
                # Simpan keypoints saat ini untuk frame berikutnya
                self._prev_keypoints[track_id] = kpts
    
    def identify_barber_for_chair(self, chair_id, rois, tracked_objects):
        """Identify which track_id is the barber for a given chair.
        
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
            
            # Check if person is inside ROI (customer)
            is_inside_roi = (chair_roi[0] <= centroid[0] <= chair_roi[2] and 
                            chair_roi[1] <= centroid[1] <= chair_roi[3])
            
            if is_inside_roi:
                continue  # Skip customers
            
            # Get posture
            posture = None
            if track_id in self.posture_history and self.posture_history[track_id]:
                posture = self.posture_history[track_id][-1]
            
            if posture != 'STANDING':
                continue  # Barber should be standing
            
            # Check proximity to chair
            distance = np.sqrt((centroid[0] - chair_center[0])**2 + (centroid[1] - chair_center[1])**2)
            if distance > 200:  # Max distance from chair (pixels)
                continue
            
            barber_candidates.append((track_id, distance))
        
        if not barber_candidates:
            return None
        
        # Return closest standing person to chair
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
