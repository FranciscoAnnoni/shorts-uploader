"""
Corre este script una sola vez para guardar las sesiones de cada plataforma.
Uso: python setup_sessions.py
"""
import asyncio
from playwright.async_api import async_playwright
from config import SESSIONS_DIR, YT_STUDIO_URL, TIKTOK_UPLOAD_URL, META_BUSINESS_URL

PLATFORMS = [
    ("youtube",   YT_STUDIO_URL,       "Logueate en YouTube Studio y presiona Enter cuando termines: "),
    ("tiktok",    TIKTOK_UPLOAD_URL,    "Logueate en TikTok y presiona Enter cuando termines: "),
    ("instagram", META_BUSINESS_URL,   "Logueate en Meta Business Suite y presiona Enter cuando termines: "),
]

async def save_session(platform: str, url: str, prompt: str):
    session_path = str(SESSIONS_DIR / platform)
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            session_path,
            headless=False,
            args=["--start-maximized"],
        )
        page = await context.new_page()
        await page.goto(url)
        input(prompt)
        await context.close()
    print(f"[OK] Sesion guardada: {platform}")

async def main():
    for platform, url, prompt in PLATFORMS:
        await save_session(platform, url, prompt)

if __name__ == "__main__":
    asyncio.run(main())
