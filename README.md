# Shorts Uploader

App local en Python que sube un Short a YouTube, TikTok e Instagram simultáneamente y los programa para publicarse a las 17:00 ART.

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
2. Correr `shorts` en terminal (o `./start.sh`)
3. Completar el form y presionar **SUBIR A LAS 3 PLATAFORMAS**
4. Cerrar la app — las plataformas publican solas a las 17:00

## Si la sesion expira (te pide loguear de nuevo)

```bash
python setup_sessions.py
```

Solo para la plataforma que falló.

## Estructura

```
~/Proyectos/shorts-uploader/    # codigo
~/shorts-uploader/pending/      # videos a subir (entrada)
~/shorts-uploader/finalized/    # videos ya subidos + metadata JSON
```
