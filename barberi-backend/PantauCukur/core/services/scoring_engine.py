import os
import numpy as np
from dotenv import load_dotenv

class ScoringEngine:
    """Scoring calculation logic for session evaluation."""
    
    def __init__(self):
        load_dotenv()
        self.hand_activity_weight = float(os.environ.get('HAND_ACTIVITY_WEIGHT', '0.35'))
        self.posture_weight = float(os.environ.get('POSTURE_WEIGHT', '0.20'))
        self.temporal_weight = float(os.environ.get('TEMPORAL_WEIGHT', '0.25'))
        self.person_count_weight = float(os.environ.get('PERSON_COUNT_WEIGHT', '0.20'))
    
    def calculate(self, chair_id, track_manager, rois, duration):
        """Hitung skor sesi keseluruhan untuk suatu kursi."""
        # 1. Posture Score (20%)
        posture_score = self.calculate_posture_score(chair_id, track_manager, rois)
        
        # 2. Hand Activity Score (35%)
        hand_score = self.calculate_hand_score(chair_id, track_manager, rois)
        
        # 3. Temporal Score (25%)
        temporal_score = self.calculate_temporal_score(duration)
        
        # 4. Person Count Score (20%)
        person_count_score = self.calculate_person_count_score(chair_id, track_manager, rois)
        
        # Weighted sum
        total_score = (
            posture_score * self.posture_weight +
            hand_score * self.hand_activity_weight +
            temporal_score * self.temporal_weight +
            person_count_score * self.person_count_weight
        )
        
        return int(total_score), {
            'posture': posture_score,
            'hand_activity': hand_score,
            'temporal': temporal_score,
            'person_count': person_count_score
        }
    
    def calculate_posture_score(self, chair_id, track_manager, rois):
        """Calculate posture score based on sitting/standing combo history."""
        # Get all track_ids associated with this chair
        track_ids = []
        for tid, traj in track_manager.trajectories.items():
            # Check if trajectory centroid is within any ROI for this chair
            if traj:
                centroid = traj[-1] if traj else None
                if centroid and chair_id < len(rois):
                    roi = rois[chair_id]
                    if (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3]):
                        track_ids.append(tid)
        
        if len(track_ids) < 2:
            return 0  # Need at least 2 persons for combo
        
        # Collect posture history for persons in this chair
        sitting_frames = 0
        total_frames = 0
        
        for tid in track_ids:
            if tid in track_manager.posture_history:
                for posture in track_manager.posture_history[tid]:
                    total_frames += 1
                    if posture == 'SITTING':
                        sitting_frames += 1
        
        if total_frames == 0:
            return 0
            
        # Hitung persentase waktu dengan 1 duduk + 1 berdiri
        # Untuk mempermudah, kita periksa apakah kita memiliki setidaknya satu duduk dan satu berdiri di frame terbaru
        # Lebih canggih: lacak kombinasi per frame
        combo_frames = 0
        min_len = min(len(track_manager.posture_history.get(tid, [])) for tid in track_ids)
        
        for i in range(min_len):
            postures = [track_manager.posture_history[tid][i] for tid in track_ids if i < len(track_manager.posture_history.get(tid, []))]
            if len(postures) >= 2:
                sitting_count = sum(1 for p in postures if p == 'SITTING')
                standing_count = len(postures) - sitting_count
                if sitting_count >= 1 and standing_count >= 1:
                    combo_frames += 1
        
        if min_len == 0:
            return 0
        
        combo_ratio = combo_frames / min_len
        
        if combo_ratio > 0.8:
            return 100
        elif combo_ratio > 0.5:
            return 70
        elif combo_ratio > 0.3:
            return 40
        else:
            return 0
    
    def calculate_hand_score(self, chair_id, track_manager, rois, tracked_objects=None):
        """Calculate hand activity score (0-100) based on barber's hand activity only."""
        # Identify barber for this chair
        barber_track_id = track_manager.identify_barber_for_chair(chair_id, rois, tracked_objects or [])
        
        if barber_track_id is None:
            # Fallback: use all persons in chair (old behavior)
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
        
        # Use only barber's hand activity
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
    
    def calculate_person_count_score(self, chair_id, track_manager, rois):
        """Calculate person count score based on how often 2 persons are present."""
        # Count frames where 2 persons were detected in this chair's ROI
        two_person_frames = 0
        total_frames = 0
        
        # We need to track per-frame person count history
        # For simplicity, use trajectory data
        track_ids_in_chair = []
        for tid, traj in track_manager.trajectories.items():
            if traj:
                centroid = traj[-1]
                if chair_id < len(rois):
                    roi = rois[chair_id]
                    if (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3]):
                        track_ids_in_chair.append(tid)
        
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
