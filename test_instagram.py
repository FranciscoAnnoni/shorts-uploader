"""
Test aislado de Instagram. Corre solo el uploader con logs en cada paso.
Uso: python test_instagram.py
"""
import asyncio
from datetime import datetime, timedelta
import pytz
from uploaders.instagram import upload

ART_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

async def main():
    video_path = input("Path al video de prueba: ").strip()
    now = datetime.now(ART_TZ).replace(tzinfo=None)
    schedule_dt = (now + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    print(f"Programando para: {schedule_dt.strftime('%Y-%m-%d %H:%M')} ART")

    result = await upload(
        video_path=video_path,
        caption="[TEST] Video de prueba automatico\n\nDescripcion de prueba. Este video fue subido por el bot.\n\n#test #prueba #frannoni",
        schedule_dt=schedule_dt,
    )
    print(f"Resultado: {result}")

if __name__ == "__main__":
    asyncio.run(main())
