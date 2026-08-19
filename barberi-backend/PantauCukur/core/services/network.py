# C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\network.py
import requests
from logger import log_event, smart_logger


class PantauNetwork:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.start_url = f"{base_url}/api/session/start/"
        self.end_url = f"{base_url}/api/session/end/"
        self.update_url = f"{base_url}/api/session/update/"
        self.heartbeat_url = f"{base_url}/api/session/heartbeat/"
        
        smart_logger.log_if_needed(
            component_key="network",
            event="NETWORK_INIT",
            level="INFO",
            base_url=base_url,
            force=True
        )

    def report_status_change(self, chair_id, is_occupied):
        """Mengirim data ke Django hanya saat ada perubahan (binary occupancy)"""
        target_url = self.start_url if is_occupied else self.end_url
        action = "START" if is_occupied else "END"

        try:
            smart_logger.log_if_needed(
                component_key="network",
                event="API_REQUEST",
                level="DEBUG",
                url=target_url,
                chair_id=chair_id,
                action=action
            )
            
            # Kita gunakan timeout 0.5 agar jika server mati, engine AI tidak freeze
            response = requests.post(
                target_url, json={"chair_id": chair_id}, timeout=0.5
            )
            if response.status_code == 200:
                log_event(
                    "network", "API_SUCCESS", level="INFO",
                    url=target_url, chair_id=chair_id, action=action,
                    status_code=response.status_code
                )
                print(f"[API] Kursi {chair_id}: {action} berhasil.")
                return True
            else:
                log_event(
                    "network", "API_ERROR", level="WARNING",
                    url=target_url, chair_id=chair_id, action=action,
                    status_code=response.status_code
                )
                print(f"[API] Error {response.status_code} pada Kursi {chair_id}")
                return False
        except requests.exceptions.RequestException as e:
            log_event(
                "network", "API_CONNECTION_FAILED", level="ERROR",
                url=target_url, chair_id=chair_id, action=action,
                error=str(e)
            )
            print(f"[API] Gagal terhubung ke server Django!")
            return False

    def report_session_update(self, chair_id, is_active, confidence_score, session_status, trigger_reason=None, breakdown=None, timeout_reason=None):
        """Mengirim update sesi lengkap ke Django (state machine integration)"""
        payload = {
            "chair_id": chair_id,
            "is_active": is_active,
            "confidence_score": confidence_score,
            "session_status": session_status,
        }
        if trigger_reason:
            payload["trigger_reason"] = trigger_reason
        if timeout_reason:
            payload["timeout_reason"] = timeout_reason
        if breakdown:
            payload["breakdown"] = breakdown

        try:
            smart_logger.log_if_needed(
                component_key="network",
                event="API_REQUEST",
                level="DEBUG",
                url=self.update_url,
                chair_id=chair_id,
                session_status=session_status
            )
            
            response = requests.post(
                self.update_url, json=payload, timeout=0.5
            )
            if response.status_code == 200:
                log_event(
                    "network", "SESSION_UPDATE_SUCCESS", level="INFO",
                    chair_id=chair_id, session_status=session_status,
                    confidence_score=confidence_score, status_code=response.status_code
                )
                print(f"[API] Session update Kursi {chair_id}: {session_status} (score={confidence_score})")
                return True
            else:
                log_event(
                    "network", "SESSION_UPDATE_ERROR", level="WARNING",
                    chair_id=chair_id, session_status=session_status,
                    status_code=response.status_code
                )
                print(f"[API] Error {response.status_code} pada session update Kursi {chair_id}")
                return False
        except requests.exceptions.RequestException as e:
            log_event(
                "network", "SESSION_UPDATE_FAILED", level="ERROR",
                chair_id=chair_id, session_status=session_status,
                error=str(e)
            )
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
            smart_logger.log_if_needed(
                component_key="network",
                event="API_REQUEST",
                level="DEBUG",
                url=self.heartbeat_url,
                chair_id=chair_id,
                session_status=session_status
            )
            
            response = requests.post(
                self.heartbeat_url, json=payload, timeout=0.5
            )
            if response.status_code == 200:
                log_event(
                    "network", "HEARTBEAT_SUCCESS", level="INFO",
                    chair_id=chair_id, session_status=session_status,
                    confidence_score=confidence_score
                )
                return True
            else:
                log_event(
                    "network", "HEARTBEAT_ERROR", level="WARNING",
                    chair_id=chair_id, session_status=session_status,
                    status_code=response.status_code
                )
                return False
        except requests.exceptions.RequestException as e:
            log_event(
                "network", "HEARTBEAT_FAILED", level="ERROR",
                chair_id=chair_id, session_status=session_status,
                error=str(e)
            )
            return False