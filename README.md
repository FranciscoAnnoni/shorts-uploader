# Shorts Uploader

App local en Python que sube un Short a YouTube, TikTok e Instagram simultáneamente desde una interfaz web. Permite programar la publicación para un horario específico o publicar al instante.

Construido con Playwright (automatización de browser) + Gradio (UI web local). Sin APIs de pago, sin servicios externos.

## Setup inicial (una sola vez)

```bash
cd ~/Proyectos/shorts-uploader
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python setup_sessions.py   # abre browser para login en cada plataforma
```

## Uso diario

1. Copiar el video a `~/shorts-uploader/pending/`
2. Abrir la app (`./start.sh` o desde el Dock)
3. Completar título, descripción, hashtags y preset del día
4. Elegir fecha/hora de publicación (default: 17:00 ART)
5. Presionar **SUBIR A LAS 3 PLATAFORMAS**
6. Cerrar la app — las plataformas publican solas a la hora programada

## Si la sesión expira

```bash
python setup_sessions.py
```

Solo para la plataforma que falló.

## Estructura

```
~/Proyectos/shorts-uploader/    # código
~/shorts-uploader/pending/      # videos a subir (entrada)
~/shorts-uploader/finalized/    # videos ya subidos + metadata JSON
sessions/                       # cookies de login por plataforma (no commiteado)
```

## Stack

- **Playwright** — automatización del browser para subir sin APIs
- **Gradio** — UI web local, corre en `localhost:7860`
- **pytz** — manejo de timezone ART para programar publicaciones

## Próximos pasos

- [ ] Modal para elegir entre programar o publicar inmediatamente: al presionar el botón principal, aparece un modal con dos opciones — "Programar" (abre el selector de fecha/hora) y "Publicar ahora" (dispara los tres uploads en paralelo con un timeout de 3 minutos para que las plataformas procesen el video antes de finalizarlo)
- [ ] TikTok Developer API: reemplazar la automatización de browser por la API oficial una vez aprobada
- [ ] Soporte multi-video: subir más de un video en una misma sesión
