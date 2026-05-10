import os
import time
from datetime import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

API_BASE = "https://graph.instagram.com/v21.0"
IG_USER_ID = os.environ["IG_USER_ID"]
ACCESS_TOKEN = os.environ["IG_ACCESS_TOKEN"]


def _get(path, params: dict):
    resp = requests.get(f"{API_BASE}/{path}", params={"access_token": ACCESS_TOKEN, **params})
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Meta API error: {data['error']}")
    return data


def _post(path, payload: dict):
    resp = requests.post(f"{API_BASE}/{path}", data={"access_token": ACCESS_TOKEN, **payload})
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Meta API error: {data['error']}")
    return data


def _upload_to_catbox(video_path: str) -> str:
    size_kb = Path(video_path).stat().st_size // 1024
    print(f"[IG] Subiendo a catbox.moe ({size_kb}KB)...")
    with open(video_path, "rb") as f:
        resp = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (Path(video_path).name, f, "video/mp4")},
            timeout=120,
        )
    if not resp.ok or not resp.text.startswith("https://"):
        raise RuntimeError(f"catbox error: {resp.status_code} {resp.text}")
    url = resp.text.strip()
    print(f"[IG] URL publica: {url}")
    return url


def _create_container(video_url: str, caption: str, scheduled_ts: int | None) -> str:
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
    }
    if scheduled_ts:
        payload["published"] = "false"
        payload["scheduled_publish_time"] = str(scheduled_ts)
    data = _post(f"{IG_USER_ID}/media", payload)
    return data["id"]


def _wait_for_finish(container_id: str, timeout: int = 300):
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = _get(container_id, {"fields": "status_code,status"})
        status = data.get("status_code", "")
        print(f"[IG] status: {status}")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Container error: {data}")
        time.sleep(10)
    raise TimeoutError("Video processing timeout")


def _publish(container_id: str):
    _post(f"{IG_USER_ID}/media_publish", {"creation_id": container_id})


async def upload(video_path: str, caption: str, schedule_dt: datetime) -> str:
    from datetime import timezone
    now_ts = int(datetime.now(timezone.utc).timestamp())
    target_ts = int(schedule_dt.timestamp())
    scheduled_ts = target_ts if target_ts - now_ts > 60 else None

    print("[IG] 1. Subiendo video a hosting temporal...")
    video_url = _upload_to_catbox(video_path)

    print("[IG] 2. Creando container en Instagram...")
    container_id = _create_container(video_url, caption, scheduled_ts)
    print(f"[IG] container_id={container_id}")

    print("[IG] 3. Esperando procesamiento...")
    _wait_for_finish(container_id)

    print("[IG] 4. Publicando...")
    _publish(container_id)

    if scheduled_ts:
        print(f"[IG] Reel programado para {schedule_dt.strftime('%Y-%m-%d %H:%M %Z')}.")
    else:
        print("[IG] Reel publicado inmediatamente.")
    return "ok"
