"""
Login de YouTube Data API, una sola vez. Abre el browser para autorizar el canal
y guarda el token en ~/.config/shorts-uploader/youtube-token.json.
Uso: python setup_youtube_api.py
"""
from google_auth_oauthlib.flow import InstalledAppFlow
from config import YT_CLIENT_SECRET_FILE, YT_TOKEN_FILE, YT_SCOPES

if not YT_CLIENT_SECRET_FILE.exists():
    raise SystemExit(f"Falta el cliente OAuth: descargar el JSON y guardarlo en {YT_CLIENT_SECRET_FILE}")

flow = InstalledAppFlow.from_client_secrets_file(str(YT_CLIENT_SECRET_FILE), YT_SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
YT_TOKEN_FILE.write_text(creds.to_json())
YT_TOKEN_FILE.chmod(0o600)
print(f"[OK] Token guardado en {YT_TOKEN_FILE}")
