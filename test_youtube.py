"""
Test aislado de YouTube. Corre solo el uploader de YouTube con logs en cada paso.
Uso: python test_youtube.py
"""
import asyncio
from datetime import datetime, timedelta
import pytz
from uploaders.youtube import upload

ART_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

async def main():
    video_path = input("Path al video de prueba: ").strip()
    now = datetime.now(ART_TZ).replace(tzinfo=None)
    schedule_dt = (now + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    print(f"Programando para: {schedule_dt.strftime('%Y-%m-%d %H:%M')} ART")

    result = await upload(
        video_path=video_path,
        title="[TEST] Video de prueba automatico",
        description="Descripcion de prueba. Este video fue subido por el bot.",
        hashtags="#test #prueba #frannoni",
        keywords=["test", "prueba"],
        language="es",
        category_id="27",
        schedule_dt=schedule_dt,
    )
    print(f"Resultado: {result}")

if __name__ == "__main__":
    asyncio.run(main())
