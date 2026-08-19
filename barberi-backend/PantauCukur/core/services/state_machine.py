# C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\state_machine.py
import os
import time
import numpy as np
from dotenv import load_dotenv
from logger import log_event  # ← TAMBAHKAN

class StateMachine:
    """Mesin status untuk manajemen siklus sesi."""
    
    def __init__(self):
        self.states = {}
        self.timers = {}
        self.scores = {}
        self.pending_start = {}
        self.last_update = {}
        self.last_score = {}  # ← TAMBAHKAN untuk breakdown saat log
        self.last_breakdown = {}  # ← TAMBAHKAN
        
        load_dotenv()
        self.pending_duration = int(os.environ.get('PENDING_DURATION', '30'))
        self.scoring_threshold = int(os.environ.get('SCORING_THRESHOLD', '70'))
        self.confirmation_window = int(os.environ.get('CONFIRMATION_WINDOW', '10'))
        self.cooldown_seconds = int(os.environ.get('COOLDOWN_SECONDS', '5'))
        self.min_valid_duration = int(os.environ.get('MIN_VALID_DURATION', '180'))
        self.session_timeout_seconds = int(os.environ.get('SESSION_TIMEOUT_SECONDS', '300'))
        self.session_timeout_action = os.environ.get('SESSION_TIMEOUT_ACTION', 'auto_end')
    
    def update(self, chair_id, score, person_count, duration, breakdown=None):
        """Perbarui mesin status untuk kursi tertentu.
        
        Returns:
            tuple: (status_baru, status_berubah, timeout_terjadi, trigger_reason)
        """
        if chair_id not in self.states:
            self.states[chair_id] = 'IDLE'
            self.timers[chair_id] = 0
            self.scores[chair_id] = []
            self.pending_start[chair_id] = None
            self.last_update[chair_id] = time.time()
            self.last_score[chair_id] = 0
            self.last_breakdown[chair_id] = {}
        
        self.last_update[chair_id] = time.time()
        
        current_state = self.states[chair_id]
        new_state = current_state
        status_changed = False
        timeout_occurred = False
        trigger_reason = None
        
        self.timers[chair_id] += 1
        
        self.scores[chair_id].append(score)
        if len(self.scores[chair_id]) > self.confirmation_window:
            self.scores[chair_id].pop(0)
        
        avg_score = np.mean(self.scores[chair_id]) if self.scores[chair_id] else 0
        
        # --- TRANSISI STATUS ---
        if current_state == 'IDLE':
            if person_count >= 2 and duration >= self.pending_duration:
                new_state = 'PENDING'
                self.pending_start[chair_id] = duration
                status_changed = True
                trigger_reason = "two_persons_detected"
        
        elif current_state == 'PENDING':
            if avg_score >= self.scoring_threshold:
                new_state = 'ACTIVE'
                status_changed = True
                trigger_reason = "score_threshold_met"
            elif person_count < 2:
                new_state = 'IDLE'
                status_changed = True
                trigger_reason = "person_count_below_two"
        
        elif current_state == 'ACTIVE':
            if avg_score < self.scoring_threshold and len(self.scores[chair_id]) >= self.confirmation_window:
                new_state = 'ENDING'
                status_changed = True
                trigger_reason = "score_below_threshold"
        
        elif current_state == 'ENDING':
            if self.timers[chair_id] >= self.cooldown_seconds:
                new_state = 'IDLE'
                status_changed = True
                trigger_reason = "cooldown_complete"
        
        # --- LOGGING HANYA SAAT STATUS BERUBAH ---
        if status_changed:
            log_event(
                component="state_machine",
                event="STATE_TRANSITION",
                level="INFO",
                chair_id=chair_id,
                from_state=current_state,
                to_state=new_state,
                trigger_reason=trigger_reason,
                score=score,
                breakdown=breakdown or self.last_breakdown.get(chair_id, {}),
                duration_in_state=self.timers[chair_id]
            )
            self.last_breakdown[chair_id] = breakdown or {}
        
        if new_state != current_state:
            self.states[chair_id] = new_state
            self.timers[chair_id] = 0
            self.scores[chair_id] = []
        
        return new_state, status_changed, timeout_occurred, trigger_reason
    
    
    def check_timeout(self, chair_id):
        """Check if session has been active too long without updates.
        
        Returns:
            bool: True if timeout occurred and action should be taken
        """
        if chair_id not in self.states:
            return False
        
        current_state = self.states[chair_id]
        if current_state not in ('ACTIVE', 'PENDING'):
            return False
        
        last_time = self.last_update.get(chair_id, 0)
        elapsed = time.time() - last_time
        
        if elapsed > self.session_timeout_seconds:
            if self.session_timeout_action == 'auto_end':
                # Force transition to ENDING
                self.states[chair_id] = 'ENDING'
                self.timers[chair_id] = 0
                self.scores[chair_id] = []
                return True
            elif self.session_timeout_action == 'alert':
                # Just alert, don't auto-end
                return True
        return False
    
    def get_state(self, chair_id):
        return self.states.get(chair_id, 'IDLE')
    
    def get_last_update_time(self, chair_id):
        return self.last_update.get(chair_id, 0)
