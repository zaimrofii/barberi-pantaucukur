# network.py
import requests


class PantauNetwork:
    def __init__(self, base_url="http://localhost:8000"):
        self.start_url = f"{base_url}/api/session/start/"
        self.end_url = f"{base_url}/api/session/end/"

    def report_status_change(self, chair_id, is_occupied):
        """Mengirim data ke Django hanya saat ada perubahan"""
        target_url = self.start_url if is_occupied else self.end_url

        try:
            # Kita gunakan timeout 0.5 agar jika server mati, engine AI tidak freeze
            response = requests.post(
                target_url, json={"chair_id": chair_id}, timeout=0.5
            )
            if response.status_code == 200:
                action = "START" if is_occupied else "END"
                print(f"[API] Kursi {chair_id}: {action} berhasil.")
            else:
                print(f"[API] Error {response.status_code} pada Kursi {chair_id}")
        except requests.exceptions.RequestException:
            print(f"[API] Gagal terhubung ke server Django!")

    def report_status_change(self, chair_id, is_occupied):
        try:
            response = requests.post(
                f"{self.base_url}/api/status/",
                json={"chair_id": chair_id, "occupied": is_occupied},
                timeout=2,
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] Network: {e}")
            return False
