import os
import numpy as np
from dotenv import load_dotenv

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
