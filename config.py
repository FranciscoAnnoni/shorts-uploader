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

# YouTube Data API: cliente OAuth (Desktop) de Google Cloud y token guardado
YT_CLIENT_SECRET_FILE = Path.home() / ".config" / "shorts-uploader" / "youtube-client-secret.json"
YT_TOKEN_FILE = Path.home() / ".config" / "shorts-uploader" / "youtube-token.json"
YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/creator-center/upload"
META_BUSINESS_URL = "https://business.facebook.com/latest/home"

# Limites
TIKTOK_CAPTION_MAX_CHARS = 2200

# Instagram: lo programa n8n en skynet (ver ~/Proyectos/ig-scheduler)
IG_QUEUE_SSH_HOST = "skynet"
IG_QUEUE_DIR = "/opt/stacks/ig-queue"
IG_WEBHOOK_URL = "http://skynet:5678/webhook/ig-encolar"  # MagicDNS de Tailscale
IG_UPLOADER_KEY_FILE = Path.home() / ".config" / "shorts-uploader" / "ig-uploader-key"
