import numpy as np
import os
from dotenv import load_dotenv

# COCO keypoint indices for YOLO-Pose
NOSE = 0
LEFT_EYE = 1
RIGHT_EYE = 2
LEFT_EAR = 3
RIGHT_EAR = 4
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_HIP = 11
RIGHT_HIP = 12

# Load configuration
load_dotenv()
HEAD_DETECTION_METHOD = os.environ.get('HEAD_DETECTION_METHOD', 'hybrid')
FACE_KEYPOINT_CONFIDENCE = float(os.environ.get('FACE_KEYPOINT_CONFIDENCE', '0.3'))
HEAD_BBOX_EXPAND_RATIO = float(os.environ.get('HEAD_BBOX_EXPAND_RATIO', '1.5'))
BARBER_STANDING_THRESHOLD = float(os.environ.get('BARBER_STANDING_THRESHOLD', '0.5'))
BARBER_PROXIMITY_THRESHOLD = float(os.environ.get('BARBER_PROXIMITY_THRESHOLD', '100'))


def get_face_bbox(kpts, confidence_threshold=0.3):
    """Calculate face bounding box from facial keypoints.
    
    Returns:
        tuple: (x_min, y_min, x_max, y_max) or None if not enough keypoints
    """
    face_indices = [NOSE, LEFT_EYE, RIGHT_EYE, LEFT_EAR, RIGHT_EAR]
    valid_points = []
    
    for idx in face_indices:
        if idx < len(kpts) and kpts[idx][2] >= confidence_threshold:
            valid_points.append((kpts[idx][0], kpts[idx][1]))
    
    if len(valid_points) < 3:
        return None
    
    xs = [p[0] for p in valid_points]
    ys = [p[1] for p in valid_points]
    
    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)
    
    # Expand bounding box
    width = x_max - x_min
    height = y_max - y_min
    expand_x = width * (HEAD_BBOX_EXPAND_RATIO - 1) / 2
    expand_y = height * (HEAD_BBOX_EXPAND_RATIO - 1) / 2
    
    x_min = max(0, x_min - expand_x)
    x_max = x_max + expand_x
    y_min = max(0, y_min - expand_y)
    y_max = y_max + expand_y
    
    return (x_min, y_min, x_max, y_max)


def get_shoulder_avg(kpts, confidence_threshold=0.3):
    """Get average position of shoulders.
    
    Returns:
        tuple: (x, y) or None if shoulders not reliable
    """
    if (LEFT_SHOULDER < len(kpts) and kpts[LEFT_SHOULDER][2] >= confidence_threshold and
        RIGHT_SHOULDER < len(kpts) and kpts[RIGHT_SHOULDER][2] >= confidence_threshold):
        x = (kpts[LEFT_SHOULDER][0] + kpts[RIGHT_SHOULDER][0]) / 2
        y = (kpts[LEFT_SHOULDER][1] + kpts[RIGHT_SHOULDER][1]) / 2
        return (x, y)
    return None


def get_head_center(kpts, confidence_threshold=0.3, method='hybrid'):
    """Get head center using multiple methods.
    
    Args:
        kpts: keypoints array (17, 3)
        confidence_threshold: minimum confidence for keypoints
        method: 'face_bbox', 'nose', 'shoulder_avg', or 'hybrid'
    
    Returns:
        tuple: (x, y) or None
    """
    if method == 'face_bbox':
        face_bbox = get_face_bbox(kpts, confidence_threshold)
        if face_bbox:
            return ((face_bbox[0] + face_bbox[2]) / 2, (face_bbox[1] + face_bbox[3]) / 2)
        return None
    
    elif method == 'nose':
        if NOSE < len(kpts) and kpts[NOSE][2] >= confidence_threshold:
            return (kpts[NOSE][0], kpts[NOSE][1])
        return None
    
    elif method == 'shoulder_avg':
        return get_shoulder_avg(kpts, confidence_threshold)
    
    elif method == 'hybrid':
        # Try face bounding box first
        face_bbox = get_face_bbox(kpts, confidence_threshold)
        if face_bbox:
            return ((face_bbox[0] + face_bbox[2]) / 2, (face_bbox[1] + face_bbox[3]) / 2)
        
        # Fallback to nose
        if NOSE < len(kpts) and kpts[NOSE][2] >= confidence_threshold:
            return (kpts[NOSE][0], kpts[NOSE][1])
        
        # Fallback to shoulder average
        shoulder_center = get_shoulder_avg(kpts, confidence_threshold)
        if shoulder_center:
            # Estimate head position above shoulders
            return (shoulder_center[0], shoulder_center[1] - 0.05 * (frame_height if 'frame_height' in dir() else 100))
        
        return None
    
    return None


def is_barber_for_chair(kpts, track_id, chair_id, rois, tracked_objects, posture_history, confidence_threshold=0.3):
    """Determine if this person is the barber for a given chair.
    
    Returns:
        bool: True if this person is likely the barber
    """
    # Get posture for this track
    posture = None
    if track_id in posture_history and posture_history[track_id]:
        posture = posture_history[track_id][-1]
    
    # Get centroid of this person
    centroid = None
    for obj in tracked_objects:
        if obj.track_id == track_id:
            bbox = obj.xyxy
            centroid = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
            break
    
    if centroid is None:
        return False
    
    # Check if person is inside any ROI (customer)
    is_inside_roi = False
    for roi in rois:
        if (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3]):
            is_inside_roi = True
            break
    
    # Barber criteria:
    # 1. Not inside ROI (or standing beside ROI)
    # 2. Standing posture
    # 3. Near the chair (within proximity threshold)
    
    if is_inside_roi:
        return False  # Person inside ROI is customer
    
    if posture != 'STANDING':
        return False  # Barber should be standing
    
    # Check proximity to chair ROI
    if chair_id < len(rois):
        chair_roi = rois[chair_id]
        chair_center = ((chair_roi[0] + chair_roi[2]) / 2, (chair_roi[1] + chair_roi[3]) / 2)
        distance = np.sqrt((centroid[0] - chair_center[0])**2 + (centroid[1] - chair_center[1])**2)
        if distance > BARBER_PROXIMITY_THRESHOLD:
            return False  # Too far from chair
    
    return True


def calculate_hand_activity(
    kpts, 
    prev_kpts=None, 
    frame_height=None, 
    confidence_threshold=0.3,
    chair_id=None,
    rois=None,
    posture_history=None,
    tracked_objects=None,
    track_id=None
):
    """Hitung poin aktivitas tangan untuk frame saat ini (hanya untuk barber).

    Argumen:
        kpts: array numpy dengan bentuk (17, 3) di mana setiap baris adalah [x, y, kepercayaan]
        prev_kpts: titik kunci frame sebelumnya untuk perhitungan kecepatan
        frame_height: tinggi frame untuk normalisasi
        confidence_threshold: ambang kepercayaan titik kunci
        chair_id: ID kursi yang sedang diproses
        rois: daftar ROI kursi
        posture_history: riwayat postur per track_id
        tracked_objects: daftar objek ByteTrack
        track_id: ID track orang ini

    Hasil:
        int: Poin untuk frame ini (0-5)
    """
    if kpts is None or len(kpts) < 13:
        return 0
    
    # Filter: only count hand activity for barber
    if chair_id is not None and rois is not None and posture_history is not None and tracked_objects is not None and track_id is not None:
        if not is_barber_for_chair(kpts, track_id, chair_id, rois, tracked_objects, posture_history, confidence_threshold):
            return 0  # Not barber, return 0
    
    points = 0
    
    try:
        # Fungsi pembantu untuk memeriksa kepercayaan titik kunci
        def is_reliable(idx):
            return kpts[idx][2] >= confidence_threshold
        
        # Get head center using hybrid method
        head_center = get_head_center(kpts, confidence_threshold, HEAD_DETECTION_METHOD)
        if head_center is None:
            # Fallback to nose if head center not available
            if NOSE < len(kpts) and kpts[NOSE][2] >= confidence_threshold:
                head_center = (kpts[NOSE][0], kpts[NOSE][1])
            else:
                return 0  # Cannot determine head position
        
        # Ambil koordinat titik kunci (nilai piksel)
        left_wrist = kpts[LEFT_WRIST]
        right_wrist = kpts[RIGHT_WRIST]
        left_hip = kpts[LEFT_HIP]
        right_hip = kpts[RIGHT_HIP]
        
        # 1. Tangan di atas kepala (pergelangan tangan y < head_center y)
        if is_reliable(LEFT_WRIST) and left_wrist[1] < head_center[1]:
            points += 2
        if is_reliable(RIGHT_WRIST) and right_wrist[1] < head_center[1]:
            points += 2
        
        # 2. Tangan dekat kepala (< 20cm dalam koordinat ternormalisasi ~0.2)
        for wrist, idx in [(left_wrist, LEFT_WRIST), (right_wrist, RIGHT_WRIST)]:
            if is_reliable(idx):
                distance = np.sqrt((wrist[0] - head_center[0])**2 + (wrist[1] - head_center[1])**2)
                # Normalisasi dengan tinggi frame jika tersedia
                if frame_height and frame_height > 0:
                    distance /= frame_height
                if distance < 0.2:
                    points += 1
        
        # 3. Gerakan tangan cepat (jika titik kunci sebelumnya tersedia)
        if prev_kpts is not None and len(prev_kpts) >= 13:
            if is_reliable(LEFT_WRIST) and prev_kpts[LEFT_WRIST][2] >= confidence_threshold:
                left_speed = np.sqrt((left_wrist[0] - prev_kpts[LEFT_WRIST][0])**2 + 
                                    (left_wrist[1] - prev_kpts[LEFT_WRIST][1])**2)
                if frame_height and frame_height > 0:
                    left_speed /= frame_height
                if left_speed > 0.05:
                    points += 1
            if is_reliable(RIGHT_WRIST) and prev_kpts[RIGHT_WRIST][2] >= confidence_threshold:
                right_speed = np.sqrt((right_wrist[0] - prev_kpts[RIGHT_WRIST][0])**2 + 
                                    (right_wrist[1] - prev_kpts[RIGHT_WRIST][1])**2)
                if frame_height and frame_height > 0:
                    right_speed /= frame_height
                if right_speed > 0.05:
                    points += 1
        
        # 4. Tangan di sisi tubuh (pergelangan tangan dekat dengan pinggul)
        for wrist, hip, wrist_idx, hip_idx in [
            (left_wrist, left_hip, LEFT_WRIST, LEFT_HIP),
            (right_wrist, right_hip, RIGHT_WRIST, RIGHT_HIP)
        ]:
            if is_reliable(wrist_idx) and is_reliable(hip_idx):
                diff = abs(wrist[1] - hip[1])
                if frame_height and frame_height > 0:
                    diff /= frame_height
                if diff < 0.1:
                    points += 1
        
    except Exception:
        pass
    
    return min(points, 5)  # batasi maksimal 5 poin per frame
