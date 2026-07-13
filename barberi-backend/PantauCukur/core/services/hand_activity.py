import numpy as np
import os
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

def calculate_hand_activity(kpts, prev_kpts=None, frame_height=None, confidence_threshold=0.3):
    """Hitung poin aktivitas tangan untuk frame saat ini.

    Argumen:
        kpts: array numpy dengan bentuk (17, 3) di mana setiap baris adalah [x, y, kepercayaan]
        prev_kpts: titik kunci frame sebelumnya untuk perhitungan kecepatan
        frame_height: tinggi frame untuk normalisasi
        confidence_threshold: ambang kepercayaan titik kunci

    Hasil:
        int: Poin untuk frame ini (0-5)
    """
    if kpts is None or len(kpts) < 13:
        return 0
    
    points = 0
    
    try:
        # Fungsi pembantu untuk memeriksa kepercayaan titik kunci
        def is_reliable(idx):
            return kpts[idx][2] >= confidence_threshold
        
        # Ambil koordinat titik kunci (nilai piksel)
        nose = kpts[NOSE]
        left_wrist = kpts[LEFT_WRIST]
        right_wrist = kpts[RIGHT_WRIST]
        left_hip = kpts[LEFT_HIP]
        right_hip = kpts[RIGHT_HIP]
        
        # 1. Tangan di atas kepala (pergelangan tangan y < hidung y)
        if is_reliable(LEFT_WRIST) and left_wrist[1] < nose[1]:
            points += 2
        if is_reliable(RIGHT_WRIST) and right_wrist[1] < nose[1]:
            points += 2
        
        # 2. Tangan dekat kepala (< 20cm dalam koordinat ternormalisasi ~0.2)
        if is_reliable(NOSE):
            head_center = (nose[0], nose[1])
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
