import shutil
import json
from datetime import datetime
from pathlib import Path
import pytz
from config import PENDING_DIR, FINALIZED_DIR, TIMEZONE

MODE_FILE = Path(__file__).parent / "uploader-mode.json"


def load_mode() -> str:
    try:
        return json.loads(MODE_FILE.read_text()).get("mode", "publicar")
    except Exception:
        return "publicar"


def save_mode(mode: str):
    MODE_FILE.write_text(json.dumps({"mode": mode}))

ART_TZ = pytz.timezone(TIMEZONE)

def get_pending_videos() -> list[Path]:
    """Retorna lista de videos mp4/mov en pending/."""
    return sorted(
        [f for f in PENDING_DIR.glob("*") if f.suffix.lower() in (".mp4", ".mov", ".avi")],
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )

def build_caption(title: str, description: str, hashtags: str) -> str:
    """Caption para TikTok e Instagram."""
    return f"{title}\n\n{description}\n\n{hashtags}".strip()

def move_to_finalized(video_path: Path, metadata: dict):
    """Mueve el video a finalized/ y guarda un JSON con la metadata."""
    dest_video = FINALIZED_DIR / video_path.name
    shutil.move(str(video_path), str(dest_video))
    meta_path = FINALIZED_DIR / f"{video_path.stem}.json"
    meta_path.write_text(json.dumps(metadata, indent=2, default=str))

def get_schedule_datetime(date_str: str, time_str: str) -> datetime:
    """
    Convierte strings de fecha y hora a datetime aware en ART.
    date_str: 'YYYY-MM-DD'
    time_str: 'HH:MM'
    """
    naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return ART_TZ.localize(naive)
