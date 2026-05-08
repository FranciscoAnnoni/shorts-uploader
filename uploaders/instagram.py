import asyncio
from datetime import datetime
from pathlib import Path
import pytz
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import SESSIONS_DIR, META_BUSINESS_URL

ART_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

async def upload(
    video_path: str,
    caption: str,        # titulo + descripcion + hashtags ya construido
    schedule_dt: datetime,  # datetime en ART timezone
) -> str:
    """
    Sube un Reel a Instagram via Meta Business Suite y lo programa.
    Retorna "ok" o lanza excepcion.
    """
    session_path = str(SESSIONS_DIR / "instagram")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            session_path,
            headless=False,
            args=["--start-maximized"],
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        await page.goto(META_BUSINESS_URL, wait_until="networkidle")
        await asyncio.sleep(3)

        # Abrir composer
        composer_btn = page.locator('[aria-label="Crear publicacion"], button:has-text("Crear publicacion")')
        await composer_btn.click()
        await asyncio.sleep(2)

        # Seleccionar tipo Reel
        reel_option = page.locator('[role="tab"]:has-text("Reel"), button:has-text("Reel")')
        await reel_option.click()
        await asyncio.sleep(1)

        # Subir video
        file_input = page.locator('input[type="file"][accept*="video"]').first
        await file_input.set_input_files(video_path)

        # Esperar procesamiento de Meta (hasta 3 minutos)
        await page.wait_for_selector('.video-processing-indicator, [data-testid="video-processing"]',
                                     state="detached", timeout=180000)
        await asyncio.sleep(2)

        # Caption
        caption_field = page.locator('textarea[placeholder*="caption"], div[contenteditable="true"][data-testid*="caption"]').first
        await caption_field.click()
        await caption_field.type(caption, delay=40)

        # Cambiar de "Publicar ahora" a "Programar"
        schedule_radio = page.locator('[aria-label="Programar"], label:has-text("Programar")')
        await schedule_radio.click()
        await asyncio.sleep(1)

        # Fecha
        date_str = schedule_dt.strftime("%m/%d/%Y")
        date_input = page.locator('input[placeholder*="fecha"], input[type="date"]').first
        await date_input.fill(date_str)
        await page.keyboard.press("Tab")

        # Hora — Meta Business Suite usa 12hs AM/PM
        hour_12 = schedule_dt.hour % 12 or 12
        ampm = "PM" if schedule_dt.hour >= 12 else "AM"
        time_str = f"{hour_12:02d}:{schedule_dt.minute:02d} {ampm}"
        time_input = page.locator('input[placeholder*="hora"], input[type="time"]').first
        await time_input.fill(time_str)
        await page.keyboard.press("Tab")
        await asyncio.sleep(1)

        # Confirmar scheduling
        save_btn = page.locator('button:has-text("Programar"), button:has-text("Guardar")')
        await save_btn.click()
        await page.wait_for_selector('.success-message, [data-testid="post-scheduled"]', timeout=30000)

        await context.close()
    return "ok"
