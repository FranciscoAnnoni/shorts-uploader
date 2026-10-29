"""
Test aislado de YouTube por API.
Uso:
  python test_youtube.py VIDEO              sube PRIVADO (no publica nada)
  python test_youtube.py VIDEO --public     publica ya
  python test_youtube.py VIDEO --schedule   programa para dentro de 30 dias (borrarlo antes)
"""
import asyncio
import sys
import time
from datetime import datetime, timedelta
import pytz
from uploaders.youtube import upload

ART_TZ = pytz.timezone("America/Argentina/Buenos_Aires")


async def main():
    video_path, flag = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
    schedule_dt = None
    if flag == "--schedule":
        schedule_dt = (datetime.now(ART_TZ) + timedelta(days=30)).replace(second=0, microsecond=0)
        print(f"Programando para: {schedule_dt:%Y-%m-%d %H:%M} ART")
    t0 = time.monotonic()
    url = await upload(
        video_path=video_path,
        title="[TEST] Video de prueba automatico",
        description="Descripcion de prueba. Este video fue subido por el bot.",
        hashtags="#test #prueba",
        keywords=["test", "prueba"],
        language="es",
        category_id="27",
        schedule_dt=schedule_dt,
        privacy="public" if flag == "--public" else "private",
    )
    print(f"Resultado: {url} en {time.monotonic() - t0:.1f} s")

if __name__ == "__main__":
    asyncio.run(main())
