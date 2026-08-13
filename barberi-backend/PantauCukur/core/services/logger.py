import os
import sys
import time
from datetime import datetime
from loguru import logger

# ============================================================
# KONFIGURASI LOGURU
# ============================================================

# Ambil konfigurasi dari environment variable
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_ROTATION = os.environ.get("LOG_ROTATION", "100 MB")
LOG_RETENTION = os.environ.get("LOG_RETENTION", "7 days")

# Pastikan direktori logs ada
os.makedirs("logs", exist_ok=True)

# Hapus default handler
logger.remove()

# Tambahkan handler untuk file JSONL
logger.add(
    "logs/ai_engine.jsonl",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
    level=LOG_LEVEL,
    rotation=LOG_ROTATION,
    retention=LOG_RETENTION,
    serialize=True,  # Output JSON
    enqueue=True,
)

# Tambahkan handler untuk terminal (readable)
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=LOG_LEVEL,
    colorize=True,
)

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

def log_event(component, event, level="INFO", **data):
    """
    Helper untuk menulis log terstruktur.
    
    Args:
        component: Nama komponen (misal: "system", "event", "warning", "error")
        event: Nama event (misal: "ENGINE_START", "FRAME_DROP")
        level: Level log (INFO, WARNING, ERROR, DEBUG)
        **data: Data tambahan yang akan disertakan dalam log
    """
    # Siapkan data dasar
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "component": component,
        "event": event,
        "level": level.upper(),
        "frame_count": _frame_count,
    }
    
    # Gabungkan dengan data tambahan
    log_data.update(data)
    
    # Tulis log sesuai level
    message = f"{component} | {event}"
    if data:
        message += f" | {data}"
    
    if level.upper() == "WARNING":
        logger.warning(message, **log_data)
    elif level.upper() == "ERROR":
        logger.error(message, **log_data)
    elif level.upper() == "DEBUG":
        logger.debug(message, **log_data)
    else:
        logger.info(message, **log_data)

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
        log_event("error", "REDIS_CONNECTION_FAILED", level="ERROR", error=str(e))
        return False
