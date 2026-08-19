# C:\Users\zaimr\projects\barberi-pantaucukur\barberi-backend\PantauCukur\core\services\logger.py
import os
import sys
import time
import inspect
from datetime import datetime
from loguru import logger

# ============================================================
# NAMA KOMPONEN STANDAR
# ============================================================

COMPONENT_NAMES = {
    "SYSTEM": "system",
    "DETECTOR": "detector",
    "TRACK_MANAGER": "track_manager",
    "HAND_ACTIVITY": "hand_activity",
    "POSTURE": "posture",
    "SCORING": "scoring",
    "STATE_MACHINE": "state_machine",
    "NETWORK": "network",
    "ROI_MANAGER": "roi_manager",
    "MAIN": "main",
}

# ============================================================
# KONFIGURASI LOGURU
# ============================================================

# Ambil konfigurasi dari environment variable
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG").upper()
LOG_ROTATION = os.environ.get("LOG_ROTATION", "100 MB")
LOG_RETENTION = os.environ.get("LOG_RETENTION", "7 days")

# Pastikan direktori logs ada
os.makedirs("logs", exist_ok=True)

# Hapus default handler
logger.remove()

# Tambahkan handler untuk file JSONL
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger.add(
    os.path.join(LOG_DIR, "ai_engine.jsonl"),
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
    level=LOG_LEVEL,
    rotation=LOG_ROTATION,
    retention=LOG_RETENTION,
    serialize=True,  # Output JSON
    enqueue=False,
)

# Tambahkan handler untuk terminal (readable)
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=LOG_LEVEL,
    colorize=True,
)

print(f"[LOGGER DEBUG] Writing to: {os.path.join(LOG_DIR, 'ai_engine.jsonl')}")
print(f"[LOGGER DEBUG] File exists: {os.path.exists(os.path.join(LOG_DIR, 'ai_engine.jsonl'))}")
# ============================================================
# GLOBAL VARIABEL UNTUK FRAME COUNT
# ============================================================
_frame_count = 0

def set_frame_count(count):
    """Set global frame count untuk digunakan dalam log"""
    global _frame_count
    _frame_count = count

def get_frame_count():
    """Dapatkan frame count saat ini"""
    return _frame_count

# ============================================================
# FUNGSI LOG EVENT
# ============================================================

def log_event(component, event, level="INFO", _caller_info=None, **data):
    """
    Helper untuk menulis log terstruktur.
    
    Args:
        component (str): Nama komponen (harus terdaftar di COMPONENT_NAMES).
        event (str): Nama event log.
        level (str): Level log ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        _caller_info (dict, optional): Informasi caller (file, function, line).
            Jika None, akan dideteksi otomatis via inspect.stack().
            Parameter internal - digunakan oleh SmartLogger agar caller
            yang tercatat adalah modul pemanggil, bukan SmartLogger.
        **data: Field data tambahan yang akan disertakan dalam log.
    """
    # Validasi nama komponen
    if component not in COMPONENT_NAMES.values():
        logger.warning(
            f"UNKNOWN_COMPONENT | component={component} | event={event} | "
            f"valid_components={list(COMPONENT_NAMES.values())}"
        )
    
    # CRITICAL FIX: Gunakan _caller_info jika diberikan (dari SmartLogger),
    # hanya fallback ke inspect.stack() jika _caller_info adalah None
    if _caller_info is not None:
        caller_info = _caller_info
    else:
        try:
            frame = inspect.stack()[1]
            caller_info = {
                "file": os.path.basename(frame.filename),
                "function": frame.function,
                "line": frame.lineno,
            }
        except (IndexError, AttributeError):
            caller_info = {"file": "unknown", "function": "unknown", "line": 0}
    
    # Siapkan data dasar
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "component": component,
        "event": event,
        "level": level.upper(),
        "frame_count": _frame_count,
        "file": caller_info["file"],
        "function": caller_info["function"],
        "line": caller_info["line"],
    }
    
    # Gabungkan dengan data tambahan
    log_data.update(data)
    
    # Buat message tanpa placeholder
    message = f"{component} | {event}"
    if data:
        # Tambahkan data ke message sebagai string
        data_str = " | ".join([f"{k}={v}" for k, v in data.items()])
        message += f" | {data_str}"
    
    # CRITICAL FIX: Hanya bind field dasar yang SELALU serializable
    # (string, int). Data kompleks (numpy types, objects, dicts) tetap
    # berada di message string agar tidak menyebabkan JSON serialization
    # error pada file handler. Semua handler (file JSONL + terminal)
    # tetap aktif karena menggunakan logger.bind() pada instance yang sama.
    logger.bind(
        component=component,
        event=event,
        file=caller_info["file"],
        function=caller_info["function"],
        line=caller_info["line"],
        frame_count=_frame_count,
    ).log(level.upper(), message)

# ============================================================
# SMART LOGGER - SAMPLING BERBASIS WAKTU
# ============================================================

class SmartLogger:
    """Manajemen interval logging per komponen dengan sampling berbasis waktu.
    
    SmartLogger menggantikan sampling berbasis frame (_sample_rate) dengan
    sampling berbasis waktu menggunakan ``time.time()``. Ini mengurangi
    frekuensi log dari ~7 log/detik menjadi ~0.2 log/detik tanpa kehilangan
    data penting, karena semua state changes tetap dicatat secara real-time.
    
    Attributes:
        _log_interval_seconds (float): Interval minimum antar log (default 5 detik).
        _minimal_level (str): Level minimal yang akan ditulis (default 'INFO').
        _aggregate_interval_seconds (float): Interval untuk log metrik agregat (default 60 detik).
        _performance_debug_mode (bool): Jika True, mengaktifkan log DEBUG.
    """
    
    _LEVEL_RANK = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
    _MAX_RECENT_VALUES = 1200  # Batasi penyimpanan nilai agar memory tetap aman
    
    def __init__(self):
        """Inisialisasi SmartLogger dengan konfigurasi dari environment variables."""
        self._log_interval_seconds = float(os.environ.get("LOG_SAMPLE_INTERVAL_SECONDS", "5"))
        self._minimal_level = os.environ.get("LOG_LEVEL_MINIMAL", "INFO").upper()
        self._aggregate_interval_seconds = float(os.environ.get("LOG_AGGREGATE_INTERVAL_SECONDS", "60"))
        self._performance_debug_mode = os.environ.get("PERFORMANCE_DEBUG_MODE", "true").lower() == "true"
        
        # Tracking waktu log terakhir per komponen
        self._last_log_time = {}
        self._last_aggregate_time = {}
        
        # Data agregat per komponen untuk metrik ringkasan
        self._aggregate_data = {}
    
    def _record_aggregate(self, component_key, data):
        """Catat data numerik/kategorikal untuk agregasi metrik.
        
        Dipanggil setiap kali log_if_needed dipanggil (termasuk saat log
        disampling), sehingga metrik agregat mencakup SEMUA pemrosesan frame,
        bukan hanya frame yang dipilih untuk logging.
        
        Args:
            component_key (str): Kunci komponen (misal 'hand_activity').
            data (dict): Data yang akan dicatat untuk agregasi.
        """
        agg = self._aggregate_data.setdefault(component_key, {})
        
        for key, value in data.items():
            if isinstance(value, bool):
                # Boolean tidak dihitung sebagai numerik
                continue
            elif isinstance(value, (int, float)):
                entry = agg.get(key)
                if entry is None or "counts" in entry:
                    # Buat entry baru (atau reset jika sebelumnya kategorikal)
                    entry = {
                        "sum": 0.0,
                        "count": 0,
                        "min": None,
                        "max": None,
                        "recent_values": [],
                    }
                    agg[key] = entry
                entry["sum"] += value
                entry["count"] += 1
                if entry["min"] is None or value < entry["min"]:
                    entry["min"] = value
                if entry["max"] is None or value > entry["max"]:
                    entry["max"] = value
                # Simpan nilai terbaru untuk distribusi (ring buffer)
                entry["recent_values"].append(value)
                if len(entry["recent_values"]) > self._MAX_RECENT_VALUES:
                    entry["recent_values"].pop(0)
            elif isinstance(value, str):
                entry = agg.get(key)
                if entry is None or "counts" not in entry:
                    # Buat entry baru (atau reset jika sebelumnya numerik)
                    entry = {"counts": {}, "total": 0}
                    agg[key] = entry
                entry["counts"][value] = entry["counts"].get(value, 0) + 1
                entry["total"] += 1
    
    def _build_distribution(self, values):
        """Bangun distribusi histogram sederhana dari daftar nilai.
        
        Args:
            values (list): Daftar nilai numerik.
        
        Returns:
            dict: Histogram dengan bucket dan rata-rata, atau None jika kosong.
        """
        if not values:
            return None
        
        min_v = min(values)
        max_v = max(values)
        avg = sum(values) / len(values)
        
        # Buat 5 bucket antara min dan max
        if max_v == min_v:
            buckets = {str(min_v): len(values)}
        else:
            buckets = {}
            span = (max_v - min_v) / 5.0
            for v in values:
                idx = int((v - min_v) / span) if span > 0 else 0
                idx = min(idx, 4)
                label = f"{min_v + idx * span:.2f}-{min_v + (idx + 1) * span:.2f}"
                buckets[label] = buckets.get(label, 0) + 1
        
        return {
            "avg": round(avg, 2),
            "min": round(min_v, 2),
            "max": round(max_v, 2),
            "count": len(values),
            "buckets": buckets,
        }
    
    def _log_aggregate(self, component_key, _caller_info=None):
        """Tulis log metrik agregat untuk komponen tertentu.
        
        Metrik agregat ditulis setiap ``_aggregate_interval_seconds`` (default 60 detik)
        menggunakan event 'AGGREGATE_METRICS'. Ini memberikan gambaran ringkas
        statistik pemrosesan tanpa membanjiri log.
        
        Args:
            component_key (str): Kunci komponen yang akan diagregasi.
            _caller_info (dict, optional): Informasi caller asli yang di-pass
                dari log_if_needed agar file/function/line yang tercatat
                adalah modul pemanggil, bukan SmartLogger.
        """
        agg = self._aggregate_data.get(component_key, {})
        if not agg:
            return
        
        summary = {}
        for key, entry in agg.items():
            if "counts" in entry and "total" in entry:
                # Data kategorikal (misal posture sit/stand)
                summary[key] = {
                    "distribution": entry["counts"],
                    "total": entry["total"],
                }
            elif entry.get("count", 0) > 0:
                numeric_summary = {
                    "avg": round(entry["sum"] / entry["count"], 2),
                    "min": round(entry["min"], 2) if entry["min"] is not None else None,
                    "max": round(entry["max"], 2) if entry["max"] is not None else None,
                    "count": entry["count"],
                }
                dist = self._build_distribution(entry.get("recent_values", []))
                if dist is not None:
                    numeric_summary["distribution"] = dist
                summary[key] = numeric_summary
        
        log_event(
            component=component_key,
            event="AGGREGATE_METRICS",
            level="INFO",
            _caller_info=_caller_info,
            metrics=summary,
            aggregate_interval_seconds=self._aggregate_interval_seconds,
        )
    
    def _check_aggregate(self, component_key, _caller_info=None):
        """Periksa apakah sudah waktunya menulis metrik agregat.
        
        Args:
            component_key (str): Kunci komponen yang akan diperiksa.
            _caller_info (dict, optional): Informasi caller asli yang di-pass
                dari log_if_needed.
        """
        now = time.time()
        last = self._last_aggregate_time.get(component_key, 0)
        if now - last >= self._aggregate_interval_seconds:
            self._last_aggregate_time[component_key] = now
            self._log_aggregate(component_key, _caller_info=_caller_info)
    
    def log_if_needed(self, component_key, event, level="INFO", force=False, **data):
        """Tulis log hanya jika interval waktu sudah terpenuhi.
        
        Aturan:
        - WARNING/ERROR: Selalu ditulis langsung (tidak disampling).
        - DEBUG: Hanya jika ``PERFORMANCE_DEBUG_MODE=true``, lalu disampling.
        - INFO: Selalu disampling sesuai ``_log_interval_seconds``.
        - force=True: Paksa tulis log meskipun interval belum terpenuhi
          (misal untuk perubahan skor signifikan).
        
        Data agregat selalu dicatat setiap pemanggilan, terlepas dari
        apakah log ditulis atau tidak.
        
        Args:
            component_key (str): Kunci unik komponen (misal 'hand_activity').
            event (str): Nama event log (misal 'HAND_ACTIVITY_CALCULATED').
            level (str): Level log ('DEBUG', 'INFO', 'WARNING', 'ERROR').
            force (bool): Jika True, log langsung tanpa menunggu interval.
            **data: Field data tambahan yang akan disertakan dalam log.
        
        Returns:
            bool: True jika log benar-benar ditulis, False jika disampling.
        """
        level = level.upper()
        
        # Validasi nama komponen
        if component_key not in COMPONENT_NAMES.values():
            logger.warning(
                f"UNKNOWN_COMPONENT | component={component_key} | event={event} | "
                f"valid_components={list(COMPONENT_NAMES.values())}"
            )
        
        # Tangkap caller info (pemanggil SmartLogger, bukan SmartLogger itu sendiri)
        caller_info = None
        try:
            # stack()[0] = log_if_needed, stack()[1] = pemanggil SmartLogger
            frame = inspect.stack()[1]
            caller_info = {
                "file": os.path.basename(frame.filename),
                "function": frame.function,
                "line": frame.lineno,
            }
        except (IndexError, AttributeError):
            caller_info = {"file": "unknown", "function": "unknown", "line": 0}
        
        # Selalu catat agregat, terlepas dari apakah log ditulis
        self._record_aggregate(component_key, data)
        
        # WARNING/ERROR: log langsung, tidak disampling
        if level in ("WARNING", "ERROR"):
            log_event(component=component_key, event=event, level=level, _caller_info=caller_info, **data)
            return True
        
        # DEBUG: hanya jika performance debug mode aktif
        if level == "DEBUG" and not self._performance_debug_mode:
            return False
        
        # Filter level minimal
        min_rank = self._LEVEL_RANK.get(self._minimal_level, 20)
        if self._LEVEL_RANK.get(level, 20) < min_rank:
            return False
        
        # Force: log langsung tanpa sampling
        if force:
            log_event(component=component_key, event=event, level=level, _caller_info=caller_info, **data)
            self._last_log_time[component_key] = time.time()
            self._check_aggregate(component_key, _caller_info=caller_info)
            return True
        
        # Sampling berbasis waktu
        now = time.time()
        last = self._last_log_time.get(component_key, 0)
        if now - last >= self._log_interval_seconds:
            self._last_log_time[component_key] = now
            log_event(component=component_key, event=event, level=level, _caller_info=caller_info, **data)
            self._check_aggregate(component_key, _caller_info=caller_info)
            return True
        
        return False


# Instance global SmartLogger untuk dipakai di seluruh modul
smart_logger = SmartLogger()

# ============================================================
# FUNGSI CEK KONEKSI REDIS
# ============================================================

def check_redis_connection():
    """
    Cek koneksi Redis.
    
    Returns:
        bool: True jika koneksi berhasil, False jika gagal
    """
    try:
        import redis
        client = redis.Redis(host="localhost", port=6379, db=0, socket_connect_timeout=2)
        client.ping()
        log_event("system", "REDIS_CONNECTED", level="INFO", status="connected")
        return True
    except Exception as e:
        log_event("system", "REDIS_CONNECTION_FAILED", level="ERROR", error=str(e))
        return False