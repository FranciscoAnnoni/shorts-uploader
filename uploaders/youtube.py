"""
YouTube por la Data API v3: sin browser. Sube el archivo por upload reanudable
y publica ya (public) o programa (private + publishAt).
Login una sola vez con: python setup_youtube_api.py
"""
import asyncio
import re
import time
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from config import YT_CLIENT_SECRET_FILE, YT_TOKEN_FILE, YT_SCOPES

CHUNK = 8 * 1024 * 1024
RETRY_STATUS = {500, 502, 503, 504}


# Limites de la API: titulo y descripcion sin < ni >, titulo 100 caracteres,
# descripcion 5000 bytes, tags 500 caracteres en total (comas y comillas de los
# tags con espacios cuentan)
def _clean(text: str) -> str:
    return re.sub(r"[<>]", "", text)


def _fit_tags(keywords: list[str]) -> list[str]:
    tags, total = [], 0
    for k in (_clean(k).strip() for k in keywords):
        if not k:
            continue
        cost = len(k) + (2 if " " in k else 0) + (1 if tags else 0)
        if total + cost > 500:
            print(f"[YT] Tags: se pasan de 500 caracteres, quedan afuera desde {k!r}")
            break
        tags.append(k)
        total += cost
    return tags


def get_credentials() -> Credentials:
    if not YT_TOKEN_FILE.exists():
        raise RuntimeError("YouTube sin login. Correr: python setup_youtube_api.py")
    creds = Credentials.from_authorized_user_file(str(YT_TOKEN_FILE), YT_SCOPES)
    if not creds.valid:
        creds.refresh(Request())
        YT_TOKEN_FILE.write_text(creds.to_json())
    return creds


def _upload_sync(video_path, body, on_confirmed) -> str:
    youtube = build("youtube", "v3", credentials=get_credentials(), cache_discovery=False)
    media = MediaFileUpload(video_path, chunksize=CHUNK, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response, last_pct, retries = None, -1, 0
    while response is None:
        try:
            status, response = request.next_chunk()
            retries = 0
            if status and int(status.progress() * 100) // 10 != last_pct:
                last_pct = int(status.progress() * 100) // 10
                print(f"[YT] Subiendo... {int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status not in RETRY_STATUS or retries >= 5:
                raise
            retries += 1
            print(f"[YT] HTTP {e.resp.status}, reintento {retries}/5...")
            time.sleep(2 ** retries)

    video_id = response["id"]
    st = response.get("status", {})
    print(f"[YT] Listo: id={video_id} privacy={st.get('privacyStatus')} "
          f"publishAt={st.get('publishAt')} upload={st.get('uploadStatus')}")
    if on_confirmed:
        on_confirmed()
    return f"https://youtube.com/shorts/{video_id}"


async def upload(
    video_path: str,
    title: str,
    description: str,
    hashtags: str,
    keywords: list[str],
    language: str,
    category_id: str,
    schedule_dt: datetime,
    on_confirmed=None,
    privacy: str = "public",
) -> str:
    status = {"selfDeclaredMadeForKids": False, "embeddable": True}
    if schedule_dt is None:
        status["privacyStatus"] = privacy
    else:
        # programado = privado con publishAt (UTC); YouTube lo pasa a publico a esa hora
        status["privacyStatus"] = "private"
        status["publishAt"] = schedule_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    body = {
        "snippet": {
            "title": " ".join(_clean(title).split())[:100],
            "description": _clean(f"{description}\n\n{hashtags}".strip())
                .encode()[:5000].decode(errors="ignore"),
            "tags": _fit_tags(keywords),
            "categoryId": category_id,
            "defaultLanguage": language,
            "defaultAudioLanguage": language,
        },
        "status": status,
    }
    when = f", publica {status['publishAt']}" if schedule_dt else ""
    print(f"[YT] API: subiendo {video_path} ({status['privacyStatus']}{when})")
    return await asyncio.to_thread(_upload_sync, video_path, body, on_confirmed)
