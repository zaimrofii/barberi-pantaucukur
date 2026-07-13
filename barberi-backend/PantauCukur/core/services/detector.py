        # detector.py
        import cv2
        from ultralytics import YOLO
        from boxmot import ByteTrack
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

        class StateMachine:
            """Mesin status untuk manajemen siklus sesi."""
            
            def __init__(self):
                self.states = {}      # chair_id -> status saat ini
                self.timers = {}      # chair_id -> timer (detik dalam status saat ini)
                self.scores = {}      # chair_id -> daftar skor terbaru untuk jendela konfirmasi
                self.pending_start = {}  # chair_id -> timestamp saat PENDING dimulai
                
                # Muat konfigurasi
                load_dotenv()
                self.pending_duration = int(os.environ.get('PENDING_DURATION', '30'))
                self.scoring_threshold = int(os.environ.get('SCORING_THRESHOLD', '70'))
                self.confirmation_window = int(os.environ.get('CONFIRMATION_WINDOW', '10'))
                self.cooldown_seconds = int(os.environ.get('COOLDOWN_SECONDS', '5'))
                self.min_valid_duration = int(os.environ.get('MIN_VALID_DURATION', '180'))
            
            def update(self, chair_id, score, person_count, duration):
                """Perbarui mesin status untuk kursi tertentu.
                
                Returns:
                    tuple: (status_baru, status_berubah)
                """
                if chair_id not in self.states:
                    self.states[chair_id] = 'IDLE'
                    self.timers[chair_id] = 0
                    self.scores[chair_id] = []
                    self.pending_start[chair_id] = None
                
                current_state = self.states[chair_id]
                new_state = current_state
                status_changed = False
                
                # Perbarui timer
                self.timers[chair_id] += 1  # asumsikan dipanggil setiap detik
                
                # Simpan skor terbaru untuk jendela konfirmasi
                self.scores[chair_id].append(score)
                if len(self.scores[chair_id]) > self.confirmation_window:
                    self.scores[chair_id].pop(0)
                
                # Hitung skor rata-rata selama jendela konfirmasi
                avg_score = np.mean(self.scores[chair_id]) if self.scores[chair_id] else 0
                
                # Transisi status
                if current_state == 'IDLE':
                    # Transisi ke PENDING ketika 2 orang hadir selama pending_duration
                    if person_count >= 2 and duration >= self.pending_duration:
                        new_state = 'PENDING'
                        self.pending_start[chair_id] = duration
                        status_changed = True
                
                elif current_state == 'PENDING':
                    # Transisi ke ACTIVE ketika skor >= threshold
                    if avg_score >= self.scoring_threshold:
                        new_state = 'ACTIVE'
                        status_changed = True
                    # Kembali ke IDLE jika jumlah orang turun di bawah 2
                    elif person_count < 2:
                        new_state = 'IDLE'
                        status_changed = True
                
                elif current_state == 'ACTIVE':
                    # Transisi ke ENDING ketika skor turun di bawah threshold selama confirmation_window
                    if avg_score < self.scoring_threshold and len(self.scores[chair_id]) >= self.confirmation_window:
                        new_state = 'ENDING'
                        status_changed = True
                
                elif current_state == 'ENDING':
                    # Setelah cooldown, kembali ke IDLE
                    if self.timers[chair_id] >= self.cooldown_seconds:
                        new_state = 'IDLE'
                        status_changed = True
                
                # Perbarui status
                if new_state != current_state:
                    self.states[chair_id] = new_state
                    self.timers[chair_id] = 0
                    self.scores[chair_id] = []
                
                return new_state, status_changed
            
            def get_state(self, chair_id):
                return self.states.get(chair_id, 'IDLE')


        class BarberDetector:
            def __init__(self, model_path='yolov8n-pose.pt', rois=None):
                print("Sistem AI: Memuat model...")
                self.model = YOLO(model_path)
                self.rois = rois if rois else []
                self.conf_threshold = 0.5
                # --- FITUR ANTI-FLICKERING ---
                self.occupancy_counters = [0] * len(self.rois)
                self.threshold_frames = 5 # Jeda frame sebelum status berubah
                self.stable_status = [False] * len(self.rois)
                
                # --- NEW: ByteTrack ---
                self.tracker = ByteTrack()
                
                # --- NEW: Session data storage ---
                self.session_data = {}
                self.state_machine = StateMachine()
                
                # --- NEW: Per-person trajectory and posture history ---
                self.trajectories = {}  # track_id -> list of centroids
                self.posture_history = {}  # track_id -> list of postures
                self.hand_activity = {}  # track_id -> accumulated hand points
                
                # --- NEW: Previous keypoints for speed calculation ---
                self._prev_keypoints = {}  # track_id -> keypoints array
                
                # --- NEW: Frame counter ---
                self.frame_count = 0
                
                # --- NEW: Configuration from .env ---
                load_dotenv()
                self.use_scoring = os.environ.get('USE_SCORING', 'false').lower() == 'true'
                self.hand_activity_weight = float(os.environ.get('HAND_ACTIVITY_WEIGHT', '0.35'))
                self.posture_weight = float(os.environ.get('POSTURE_WEIGHT', '0.20'))
                self.temporal_weight = float(os.environ.get('TEMPORAL_WEIGHT', '0.25'))
                self.person_count_weight = float(os.environ.get('PERSON_COUNT_WEIGHT', '0.20'))
                self.keypoint_conf_threshold = float(os.environ.get('KEYPOINT_CONF_THRESHOLD', '0.3'))
                
                # --- NEW: Memory leak prevention ---
                self.track_last_seen = {}  # track_id -> last frame seen
                self.track_timeout = int(os.environ.get('TRACK_TIMEOUT_SECONDS', '60')) * 30  # 60 seconds * 30 fps
                self.cleanup_counter = 0
                self.cleanup_interval = int(os.environ.get('CLEANUP_INTERVAL_FRAMES', '300'))
                
                # --- NEW: Posture classification thresholds ---
                self.sitting_area_ratio_threshold = float(os.environ.get('SITTING_AREA_RATIO_THRESHOLD', '0.55'))
                self.sitting_temporal_window = int(os.environ.get('SITTING_TEMPORAL_WINDOW', '10'))
                self.sitting_min_consistent_frames = int(os.environ.get('SITTING_MIN_CONSISTENT_FRAMES', '5'))
                self.chair_detection_confidence = float(os.environ.get('CHAIR_DETECTION_CONFIDENCE', '0.3'))
                
                print("Sistem AI: Model siap dengan YOLO-Pose, ByteTrack, dan Scoring Engine.")

            def update_rois(self, new_rois):
                self.rois = new_rois
                # Reset occupancy counters for new ROIs
                self.occupancy_counters = [0] * len(self.rois)
                self.stable_status = [False] * len(self.rois)
                print(f"ROI diperbarui: {len(self.rois)} kursi terdaftar.")

            def check_occupancy(self, person_box, roi_box):
                px1, py1, px2, py2 = person_box
                rx1, ry1, rx2, ry2 = roi_box

                # 1. Hitung koordinat tumpang tindih (intersection)
                ix1 = max(px1, rx1)
                iy1 = max(py1, ry1)
                ix2 = min(px2, rx2)
                iy2 = min(py2, ry2)

                # 2. Hitung luas area tumpang tindih
                width = max(0, ix2 - ix1)
                height = max(0, iy2 - iy1)
                intersection_area = width * height

                # 3. Hitung luas kotak kursi (ROI)
                roi_area = (rx2 - rx1) * (ry2 - ry1)

                # 4. Tentukan ambang batas (contoh: 40% dari luas kursi harus tertutup)
                occupancy_ratio = intersection_area / roi_area if roi_area > 0 else 0
            
                return occupancy_ratio > 0.4  # Ubah angka ini (0.1 - 0.9) sesuai selera sensitivitasmu

            def _calculate_area_ratio(self, bbox):
                """Calculate width/height ratio of person bounding box."""
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                return width / height if height > 0 else 0

            def _get_consistent_posture(self, track_id):
                """Get posture that has been consistent across last N frames."""
                if track_id not in self.posture_history:
                    return None
                recent = self.posture_history[track_id][-self.sitting_temporal_window:]
                if len(recent) < self.sitting_min_consistent_frames:
                    return None
                sitting_count = sum(1 for p in recent if p == 'SITTING')
                standing_count = len(recent) - sitting_count
                if sitting_count > standing_count * 2:
                    return 'SITTING'
                elif standing_count > sitting_count * 2:
                    return 'STANDING'
                return None

            def classify_posture(self, kpts, bbox=None, roi=None, frame_height=None):
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
                    
            def calculate_hand_activity(self, kpts, prev_kpts=None, frame_height=None):
                """Hitung poin aktivitas tangan untuk frame saat ini.

                Argumen:
                    kpts: array numpy dengan bentuk (17, 3) di mana setiap baris adalah [x, y, kepercayaan]
                    prev_kpts: titik kunci frame sebelumnya untuk perhitungan kecepatan
                    frame_height: tinggi frame untuk normalisasi

                Hasil:
                    int: Poin untuk frame ini (0-5)
                """
                if kpts is None or len(kpts) < 13:
                    return 0
                
                points = 0
                
                try:
                    # Fungsi pembantu untuk memeriksa kepercayaan titik kunci
                    def is_reliable(idx):
                        return kpts[idx][2] >= self.keypoint_conf_threshold
                    
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
                        if is_reliable(LEFT_WRIST) and prev_kpts[LEFT_WRIST][2] >= self.keypoint_conf_threshold:
                            left_speed = np.sqrt((left_wrist[0] - prev_kpts[LEFT_WRIST][0])**2 + 
                                                (left_wrist[1] - prev_kpts[LEFT_WRIST][1])**2)
                            if frame_height and frame_height > 0:
                                left_speed /= frame_height
                            if left_speed > 0.05:
                                points += 1
                        if is_reliable(RIGHT_WRIST) and prev_kpts[RIGHT_WRIST][2] >= self.keypoint_conf_threshold:
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

            def calculate_posture_score(self, chair_id):
                """Calculate posture score based on sitting/standing combo history."""
                # Get all track_ids associated with this chair
                track_ids = []
                for tid, traj in self.trajectories.items():
                    # Check if trajectory centroid is within any ROI for this chair
                    if traj:
                        centroid = traj[-1] if traj else None
                        if centroid and chair_id < len(self.rois):
                            roi = self.rois[chair_id]
                            if (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3]):
                                track_ids.append(tid)
                
                if len(track_ids) < 2:
                    return 0  # Need at least 2 persons for combo
                
                # Collect posture history for persons in this chair
                sitting_frames = 0
                total_frames = 0
                
                for tid in track_ids:
                    if tid in self.posture_history:
                        for posture in self.posture_history[tid]:
                            total_frames += 1
                            if posture == 'SITTING':
                                sitting_frames += 1
                
                if total_frames == 0:
                    return 0
                    
                # Hitung persentase waktu dengan 1 duduk + 1 berdiri
                # Untuk mempermudah, kita periksa apakah kita memiliki setidaknya satu duduk dan satu berdiri di frame terbaru
                # Lebih canggih: lacak kombinasi per frame
                combo_frames = 0
                min_len = min(len(self.posture_history.get(tid, [])) for tid in track_ids)
                
                for i in range(min_len):
                    postures = [self.posture_history[tid][i] for tid in track_ids if i < len(self.posture_history.get(tid, []))]
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

            def calculate_hand_score(self, chair_id):
                """Calculate hand activity score (0-100) based on accumulated points."""
                total_points = 0
                total_frames = 0
                
                for tid, points_list in self.hand_activity.items():
                    # Check if this track belongs to this chair
                    if tid in self.trajectories and self.trajectories[tid]:
                        centroid = self.trajectories[tid][-1]
                        if chair_id < len(self.rois):
                            roi = self.rois[chair_id]
                            if (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3]):
                                total_points += sum(points_list)
                                total_frames += len(points_list)
                
                if total_frames == 0:
                    return 0
                
                # Normalize to 0-100 (max 5 points per frame)
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

            def calculate_person_count_score(self, chair_id):
                """Calculate person count score based on how often 2 persons are present."""
                # Count frames where 2 persons were detected in this chair's ROI
                two_person_frames = 0
                total_frames = 0
                
                # We need to track per-frame person count history
                # For simplicity, use trajectory data
                track_ids_in_chair = []
                for tid, traj in self.trajectories.items():
                    if traj:
                        centroid = traj[-1]
                        if chair_id < len(self.rois):
                            roi = self.rois[chair_id]
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

            def calculate_score(self, chair_id, tracked_objects, landmarks_dict, duration):
                """Hitung skor sesi keseluruhan untuk suatu kursi."""
                # 1. Posture Score (20%)
                posture_score = self.calculate_posture_score(chair_id)
                
                # 2. Hand Activity Score (35%)
                hand_score = self.calculate_hand_score(chair_id)
                
                # 3. Temporal Score (25%)
                temporal_score = self.calculate_temporal_score(duration)
                
                # 4. Person Count Score (20%)
                person_count_score = self.calculate_person_count_score(chair_id)
                
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

            def cleanup_inactive_tracks(self):
                """Remove track data that hasn't been seen for > timeout frames."""
                current_frame = self.frame_count
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
                
                return len(to_remove)

            def _compute_iou(self, box1, box2):
                """Compute Intersection over Union between two bounding boxes.
                
                Args:
                    box1, box2: arrays of [x1, y1, x2, y2]
                    
                Returns:
                    float: IoU value
                """
                x1 = max(box1[0], box2[0])
                y1 = max(box1[1], box2[1])
                x2 = min(box1[2], box2[2])
                y2 = min(box1[3], box2[3])
                
                inter_area = max(0, x2 - x1) * max(0, y2 - y1)
                box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
                box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
                union_area = box1_area + box2_area - inter_area
                
                return inter_area / union_area if union_area > 0 else 0.0

            def _match_keypoints_to_tracked(self, yolo_boxes, yolo_keypoints, tracked_objects, iou_threshold=0.3):
                """Mencocokkan deteksi YOLO (dengan titik kunci) dengan objek yang dilacak ByteTrack menggunakan IoU.

                    Argumen:
                    yolo_boxes: array numpy dengan bentuk (N, 4) berisi kotak deteksi YOLO
                    yolo_keypoints: array numpy dengan bentuk (N, 17, 3) berisi titik kunci
                    tracked_objects: daftar objek ByteTrack
                    iou_threshold: IoU minimum untuk mempertimbangkan kecocokan

                    Hasil:
                    dict: track_id -> array titik kunci untuk objek yang cocok
                    """
                matched = {}
                used_yolo = set()
                
                for obj in tracked_objects:
                    track_id = obj.track_id
                    track_box = obj.xyxy  # [x1, y1, x2, y2]
                    best_iou = 0
                    best_idx = -1
                    
                    for j, yolo_box in enumerate(yolo_boxes):
                        if j in used_yolo:
                            continue
                        iou = self._compute_iou(track_box, yolo_box)
                        if iou > best_iou:
                            best_iou = iou
                            best_idx = j
                    
                    if best_iou >= iou_threshold and best_idx != -1:
                        matched[track_id] = yolo_keypoints[best_idx]
                        used_yolo.add(best_idx)
                
                return matched

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
                # tracked_objects adalah daftar deteksi dengan atribut track_id
                
                # --- Cocokkan keypoints YOLO ke objek yang dilacak ---
                frame_height = frame.shape[0]
                keypoints_per_track = {}
                if yolo_keypoints is not None and len(tracked_objects) > 0:
                    keypoints_per_track = self._match_keypoints_to_tracked(
                        person_boxes, yolo_keypoints, tracked_objects
                    )
                
                # --- Perbarui riwayat lintasan dan postur ---
                for obj in tracked_objects:
                    track_id = obj.track_id
                    bbox = obj.xyxy  # [x1, y1, x2, y2]
                    centroid = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
                    
                    # Perbarui lintasan
                    if track_id not in self.trajectories:
                        self.trajectories[track_id] = []
                    self.trajectories[track_id].append(centroid)
                    
                    # Update last seen frame
                    self.track_last_seen[track_id] = self.frame_count
                    
                    # Ambil keypoints untuk track spesifik ini
                    kpts = keypoints_per_track.get(track_id)
                    
                    if kpts is not None:
                        # Determine which ROI this track belongs to (for chair detection)
                        chair_roi = None
                        for i, roi in enumerate(self.rois):
                            if (roi[0] <= centroid[0] <= roi[2] and roi[1] <= centroid[1] <= roi[3]):
                                chair_roi = roi
                                break
                        
                        # Klasifikasikan postur dengan parameter baru
                        posture = self.classify_posture(
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
                        
                        # Hitung aktivitas tangan
                        hand_points = self.calculate_hand_activity(kpts, prev_kpts, frame_height)
                        if track_id not in self.hand_activity:
                            self.hand_activity[track_id] = []
                        self.hand_activity[track_id].append(hand_points)
                        
                        # Simpan keypoints saat ini untuk frame berikutnya
                        self._prev_keypoints[track_id] = kpts
                
                # --- Cleanup inactive tracks periodically ---
                self.cleanup_counter += 1
                if self.cleanup_counter >= self.cleanup_interval:
                    removed = self.cleanup_inactive_tracks()
                    if removed > 0:
                        print(f"[CLEANUP] Removed {removed} inactive tracks")
                    self.cleanup_counter = 0
                
                # --- Anti-kedipan (yang sudah ada) ---
                current_raw_status = [False] * len(self.rois)
                for box in person_boxes:
                    for i, roi in enumerate(self.rois):
                        if self.check_occupancy(box, roi):
                            current_raw_status[i] = True
                
                for i in range(len(self.rois)):
                    if current_raw_status[i]:
                        self.occupancy_counters[i] = min(self.occupancy_counters[i] + 1, self.threshold_frames + 1)
                    else:
                        self.occupancy_counters[i] = max(self.occupancy_counters[i] - 1, 0)
                    
                    if self.occupancy_counters[i] >= self.threshold_frames:
                        self.stable_status[i] = True
                    elif self.occupancy_counters[i] == 0:
                        self.stable_status[i] = False
                
                # --- Penilaian dan Mesin Status (jika diaktifkan) ---
                session_data = {}
                if self.use_scoring:
                    for chair_id in range(len(self.rois)):
                        if self.stable_status[chair_id]:
                            # Hitung durasi (disederhanakan: gunakan hitungan frame sebagai proksi)
                            duration = self.frame_count  # frame yang diproses
                            
                            # Hitung skor
                            score, breakdown = self.calculate_score(
                                chair_id, tracked_objects, 
                                keypoints_per_track,
                                duration
                            )
                            
                            # Perbarui mesin status
                            person_count = sum(1 for obj in tracked_objects if self.check_occupancy(
                                obj.xyxy, self.rois[chair_id]
                            ))
                            new_state, status_changed = self.state_machine.update(
                                chair_id, score, person_count, duration
                            )
                            
                            # Bangun data sesi
                            person_ids = [obj.track_id for obj in tracked_objects if self.check_occupancy(
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
                    return self.stable_status, person_boxes, session_data
                else:
                    return self.stable_status, person_boxes

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
                
