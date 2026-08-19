# C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\roi_manager.py
class ROIManager:
    """ROI and occupancy management logic."""
    
    def __init__(self, rois=None):
        self.rois = rois if rois else []
        self.occupancy_counters = [0] * len(self.rois)
        self.threshold_frames = 5  # Jeda frame sebelum status berubah
        self.stable_status = [False] * len(self.rois)
    
    def update_rois(self, new_rois):
        self.rois = new_rois
        # Reset occupancy counters for new ROIs
        self.occupancy_counters = [0] * len(self.rois)
        self.stable_status = [False] * len(self.rois)
    
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
    
    def update_occupancy(self, person_boxes):
        """Update occupancy status with anti-flickering smoothing."""
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
        
        return self.stable_status
    
    def count_persons_in_roi(self, person_boxes, chair_id):
        """Count persons in a specific ROI."""
        count = 0
        for box in person_boxes:
            if self.check_occupancy(box, self.rois[chair_id]):
                count += 1
        return count
