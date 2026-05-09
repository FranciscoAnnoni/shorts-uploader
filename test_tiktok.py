"""
Test aislado de TikTok. Corre solo el uploader con logs en cada paso.
Uso: python test_tiktok.py
"""
import asyncio
from datetime import datetime, timedelta
from uploaders.tiktok import upload

async def main():
    video_path = input("Path al video de prueba: ").strip()
    now = datetime.now()
    schedule_dt = (now + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    print(f"Programando para: {schedule_dt.strftime('%Y-%m-%d %H:%M')} ART")

    result = await upload(
        video_path=video_path,
        title="[TEST] Video de prueba automatico",
        description="Descripcion de prueba. Este video fue subido por el bot.",
        hashtags="#test #prueba #frannoni",
        schedule_dt=schedule_dt,
    )
    print(f"Resultado: {result}")

if __name__ == "__main__":
    asyncio.run(main())
