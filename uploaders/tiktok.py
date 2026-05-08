import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import pytz
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import SESSIONS_DIR, TIKTOK_UPLOAD_URL, TIKTOK_CAPTION_MAX_CHARS

ART_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

def build_caption(title: str, description: str, hashtags: str) -> str:
    caption = f"{title}\n\n{description}\n\n{hashtags}"
    return caption[:TIKTOK_CAPTION_MAX_CHARS]

async def upload(
    video_path: str,
    title: str,
    description: str,
    hashtags: str,
    schedule_dt: datetime,  # datetime en ART timezone
) -> str:
    """
    Sube video a TikTok Creator Center y lo programa.
    Retorna "ok" o lanza excepcion.
    """
    # Validar que schedule_dt este al menos 20 min en el futuro
    now_art = datetime.now(ART_TZ)
    dt_aware = ART_TZ.localize(schedule_dt) if schedule_dt.tzinfo is None else schedule_dt
    if dt_aware - now_art < timedelta(minutes=20):
        raise ValueError("TikTok requiere que el scheduling sea al menos 20 minutos en el futuro")

    caption = build_caption(title, description, hashtags)
    session_path = str(SESSIONS_DIR / "tiktok")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            session_path,
            headless=False,
            args=["--start-maximized"],
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        await page.goto(TIKTOK_UPLOAD_URL, wait_until="networkidle")
        await asyncio.sleep(3)

        # Upload del archivo
        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(video_path)

        # Esperar procesamiento del video
        await page.wait_for_selector('.upload-progress-bar', state="detached", timeout=120000)
        await asyncio.sleep(2)

        # Caption
        caption_field = page.locator('[data-text="true"]').first
        await caption_field.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.type(caption, delay=30)

        # Privacidad: Todos
        await page.select_option('select[name="privacyLevel"], [data-testid="privacy-select"]', value="PUBLIC_TO_EVERYONE")

        # Activar scheduling
        schedule_toggle = page.locator('[data-testid="schedule-toggle"], label:has-text("Programar publicacion")')
        await schedule_toggle.click()
        await asyncio.sleep(1)

        # Fecha y hora
        date_str = schedule_dt.strftime("%Y-%m-%d")
        time_str = schedule_dt.strftime("%H:%M")

        await page.fill('[placeholder*="fecha"], [data-testid="date-picker"] input', date_str)
        await page.keyboard.press("Enter")
        await page.fill('[placeholder*="hora"], [data-testid="time-picker"] input', time_str)
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)

        # Publicar
        await page.click('button:has-text("Programar"), button:has-text("Schedule")')
        await page.wait_for_selector('.upload-success, [data-testid="upload-success"]', timeout=30000)

        await context.close()
    return "ok"
