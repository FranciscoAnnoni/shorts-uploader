"""Instagram via n8n en skynet (proyecto ~/Proyectos/ig-scheduler).

Copia el video a la cola de skynet y le pide a n8n que lo programe. n8n crea
el container una hora antes y lo publica a la hora: la API de Instagram no
programa Reels. Despues de publicado, n8n borra el video de skynet.
"""
import re
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path

import requests

from config import IG_QUEUE_SSH_HOST, IG_QUEUE_DIR, IG_WEBHOOK_URL, IG_UPLOADER_KEY_FILE


def _remote_name(video_path: Path, schedule_dt: datetime) -> str:
    # n8n solo acepta letras, numeros, . _ - (se usa en comandos de borrado)
    stem = unicodedata.normalize("NFKD", video_path.stem).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()[:60] or "video"
    return f"{schedule_dt:%Y%m%d-%H%M}-{slug}{video_path.suffix.lower()}"


async def upload(video_path: str, caption: str, schedule_dt: datetime) -> str:
    video = Path(video_path)
    name = _remote_name(video, schedule_dt)

    print(f"[IG] Copiando a {IG_QUEUE_SSH_HOST}:{IG_QUEUE_DIR}/{name}...")
    subprocess.run(["scp", "-q", str(video), f"{IG_QUEUE_SSH_HOST}:{IG_QUEUE_DIR}/{name}"], check=True, timeout=1800)

    print("[IG] Programando en n8n...")
    resp = requests.post(
        IG_WEBHOOK_URL,
        json={"archivo": name, "caption": caption, "publicar_en": schedule_dt.isoformat()},
        headers={"X-Uploader-Key": IG_UPLOADER_KEY_FILE.read_text().strip()},
        timeout=60,
    )
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if not resp.ok or not data.get("ok"):
        raise RuntimeError(f"n8n: {data.get('error') or f'HTTP {resp.status_code} {resp.text[:200]}'}")
    return f"programado #{data['id']} para {data['publicar_en']}"
