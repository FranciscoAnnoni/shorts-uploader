import os
from pathlib import Path

# Carpetas de trabajo
PENDING_DIR = Path.home() / "shorts-uploader" / "pending"
FINALIZED_DIR = Path.home() / "shorts-uploader" / "finalized"
SESSIONS_DIR = Path(__file__).parent / "sessions"

# Hora de publicacion default
DEFAULT_PUBLISH_HOUR = 17
DEFAULT_PUBLISH_MINUTE = 0
TIMEZONE = "America/Argentina/Buenos_Aires"  # UTC-3, sin DST

# YouTube
YT_CATEGORIES = {
    "Education (27)": "27",
    "Science & Tech (28)": "28",
}
YT_DEFAULT_LANGUAGE = "es"
YT_DEFAULT_CATEGORY = "27"

# URLs de upload
YT_STUDIO_URL = "https://studio.youtube.com"
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/creator-center/upload"
META_BUSINESS_URL = "https://business.facebook.com/latest/home"

# Limites
TIKTOK_CAPTION_MAX_CHARS = 2200
