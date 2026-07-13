# network.py
import requests


class PantauNetwork:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.start_url = f"{base_url}/api/session/start/"
        self.end_url = f"{base_url}/api/session/end/"
        self.update_url = f"{base_url}/api/session/update/"
        self.heartbeat_url = f"{base_url}/api/session/heartbeat/"

    def report_status_change(self, chair_id, is_occupied):
        """Mengirim data ke Django hanya saat ada perubahan (binary occupancy)"""
        target_url = self.start_url if is_occupied else self.end_url

        try:
            # Kita gunakan timeout 0.5 agar jika server mati, engine AI tidak freeze
            response = requests.post(
                target_url, json={"chair_id": chair_id}, timeout=0.5
            )
            if response.status_code == 200:
                action = "START" if is_occupied else "END"
                print(f"[API] Kursi {chair_id}: {action} berhasil.")
                return True
            else:
                print(f"[API] Error {response.status_code} pada Kursi {chair_id}")
                return False
        except requests.exceptions.RequestException:
            print(f"[API] Gagal terhubung ke server Django!")
            return False

    def report_session_update(self, chair_id, is_active, confidence_score, session_status, timeout_reason=None):
        """Mengirim update sesi lengkap ke Django (state machine integration)"""
        payload = {
            "chair_id": chair_id,
            "is_active": is_active,
            "confidence_score": confidence_score,
            "session_status": session_status,
        }
        if timeout_reason:
            payload["timeout_reason"] = timeout_reason

        try:
            response = requests.post(
                self.update_url, json=payload, timeout=0.5
            )
            if response.status_code == 200:
                print(f"[API] Session update Kursi {chair_id}: {session_status} (score={confidence_score})")
                return True
            else:
                print(f"[API] Error {response.status_code} pada session update Kursi {chair_id}")
                return False
        except requests.exceptions.RequestException:
            print(f"[API] Gagal terhubung ke server Django untuk session update!")
            return False

    def send_heartbeat(self, chair_id, is_active, confidence_score, session_status):
        """Mengirim heartbeat ke Django untuk menjaga sesi tetap hidup"""
        payload = {
            "chair_id": chair_id,
            "is_active": is_active,
            "confidence_score": confidence_score,
            "session_status": session_status,
        }
        try:
            response = requests.post(
                self.heartbeat_url, json=payload, timeout=0.5
            )
            if response.status_code == 200:
                return True
            else:
                return False
        except requests.exceptions.RequestException:
            return False
