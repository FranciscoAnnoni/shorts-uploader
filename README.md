# Shorts Uploader

App local en Python que sube un Short a YouTube, TikTok e Instagram simultáneamente desde una interfaz web. Permite programar la publicación para un horario específico o publicar al instante.

Construido con Gradio (UI web local). YouTube sube por la YouTube Data API v3, sin browser; TikTok con Playwright (automatización de browser). Instagram se programa con n8n en un servidor propio (skynet) y la Graph API. Sin servicios pagos.

## Setup inicial (una sola vez)

```bash
cd ~/Proyectos/shorts-uploader
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python setup_sessions.py   # abre browser para login en cada plataforma
python setup_youtube_api.py   # login de la API de YouTube (una vez)
```

YouTube necesita un cliente OAuth "App de escritorio" de Google Cloud (proyecto con YouTube Data API v3
habilitada, app en producción para que el token no venza a los 7 días) guardado en
`~/.config/shorts-uploader/youtube-client-secret.json`. El token pide solo `youtube.upload`:
puede subir, no editar ni borrar videos. Revocar en https://myaccount.google.com/permissions.

## Uso diario

1. Copiar el video a `~/shorts-uploader/pending/`
2. Abrir la app (`./start.sh` o desde el Dock)
3. Completar título, descripción, hashtags y preset del día
4. Elegir fecha/hora de publicación (default: 17:00 ART)
5. Presionar **SUBIR A LAS 3 PLATAFORMAS**
6. Cerrar la app — las plataformas publican solas a la hora programada

## Cómo publica cada plataforma

Las tres corren en paralelo cuando se aprieta el botón.

| Plataforma | Cómo | Quién publica a la hora |
|---|---|---|
| YouTube | Data API v3 (`videos.insert`): publica ya (public) o programa (private + `publishAt`) | YouTube |
| TikTok | Playwright en TikTok Studio, deja el video programado | TikTok |
| Instagram | `scp` del video a skynet + `POST /webhook/ig-encolar` a n8n (por Tailscale, header `X-Uploader-Key`) | n8n en skynet |

La API de Instagram no programa Reels y el container que arma vence a las 24 h, así que n8n
(proyecto `~/Proyectos/ig-scheduler`) espera hasta 22 h antes, sube el video a Cloudflare R2
(bucket privado, link firmado de 2 h), crea el container, espera a que Instagram lo procese y lo
borra de R2. Si falla, reintenta cada 10 min. A la hora llama `media_publish` y avisa por Telegram.

Secretos fuera del repo: `.env` (token de Instagram), `~/.config/shorts-uploader/ig-uploader-key`
(clave del webhook), `~/.config/shorts-uploader/r2.env` (claves de R2) y
`~/.config/shorts-uploader/youtube-client-secret.json` + `youtube-token.json` (API de YouTube).

## Si la sesión expira

```bash
python setup_sessions.py
```

Solo para la plataforma que falló. Para YouTube (error de token): `python setup_youtube_api.py`.

## Estructura

```
~/Proyectos/shorts-uploader/    # código
~/shorts-uploader/pending/      # videos a subir (entrada)
~/shorts-uploader/finalized/    # videos ya subidos + metadata JSON
sessions/                       # cookies de login por plataforma (no commiteado)
```

## Stack

- **YouTube Data API v3** (google-api-python-client) — subida de YouTube
- **Playwright** — automatización del browser para TikTok
- **Gradio** — UI web local, corre en `localhost:7860`
- **pytz** — manejo de timezone ART para programar publicaciones

## Próximos pasos

- [ ] Modal para elegir entre programar o publicar inmediatamente: al presionar el botón principal, aparece un modal con dos opciones — "Programar" (abre el selector de fecha/hora) y "Publicar ahora" (dispara los tres uploads en paralelo con un timeout de 3 minutos para que las plataformas procesen el video antes de finalizarlo)
- [ ] TikTok Developer API: reemplazar la automatización de browser por la API oficial una vez aprobada
- [ ] Soporte multi-video: subir más de un video en una misma sesión
