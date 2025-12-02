# utils.py
import re
from pathlib import Path

def extract_url(text: str):
    """يستخرج أول رابط http/https من النص"""
    if not text:
        return None
    m = re.search(r'(https?://[^\s]+)', text)
    return m.group(1) if m else None

def safe_filename(s: str) -> str:
    """نعيد اسم ملف آمن"""
    # بسيط: إزالة محارف غير مسموح بها في اسماء الملفات
    keep = "".join(c for c in s if c.isalnum() or c in " ._-()[]")
    return keep.strip() or "file"

def ensure_downloads_dir(path="downloads"):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)
