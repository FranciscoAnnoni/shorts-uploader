import asyncio
from datetime import datetime
from pathlib import Path
import pytz
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import SESSIONS_DIR, YT_STUDIO_URL

ART_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

def convert_to_browser_tz(dt_art: datetime, browser_tz_name: str) -> datetime:
    """Convierte datetime en ART a la timezone del browser."""
    dt_aware = ART_TZ.localize(dt_art) if dt_art.tzinfo is None else dt_art
    browser_tz = pytz.timezone(browser_tz_name)
    return dt_aware.astimezone(browser_tz)

async def upload(
    video_path: str,
    title: str,
    description: str,
    hashtags: str,
    keywords: list[str],
    language: str,
    category_id: str,
    schedule_dt: datetime,  # datetime en ART timezone
    browser_tz: str = "Europe/Rome",  # ajustar a la timezone de la Mac del usuario
) -> str:
    """
    Sube un video a YouTube Studio y lo programa para publicarse en schedule_dt.
    Retorna "ok" o lanza excepcion con mensaje de error.
    """
    session_path = str(SESSIONS_DIR / "youtube")
    full_description = f"{description}\n\n{hashtags}"
    schedule_local = convert_to_browser_tz(schedule_dt, browser_tz)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            session_path,
            headless=False,
            args=["--start-maximized"],
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        # 1. Ir a YouTube Studio
        await page.goto(YT_STUDIO_URL, wait_until="networkidle")

        # 2. Click "Crear" -> "Subir videos"
        await page.click('[aria-label="Crear"]')
        await page.click('tp-yt-paper-item:has-text("Subir videos")')

        # 3. Subir archivo
        async with page.expect_file_chooser() as fc_info:
            await page.click('[id="select-files-button"]')
        file_chooser = await fc_info.value
        await file_chooser.set_files(video_path)

        # 4. Esperar a que aparezca el campo de titulo
        await page.wait_for_selector('[id="title-textarea"] #textbox', timeout=30000)
        await asyncio.sleep(2)

        # 5. Titulo
        title_field = page.locator('[id="title-textarea"] #textbox')
        await title_field.triple_click()
        await title_field.type(title, delay=50)

        # 6. Descripcion
        desc_field = page.locator('[id="description-textarea"] #textbox')
        await desc_field.click()
        await desc_field.type(full_description, delay=30)

        # 7. Contenido para ninos — siempre "No"
        await page.click('[id="no-radio-button"] [id="radioLabel"]')

        # 8. Mas opciones (idioma y categoria)
        await page.click('button:has-text("Mas opciones")')
        await page.wait_for_selector('[id="language-input"]', timeout=10000)
        await page.select_option('[id="language-input"]', value=language)
        await page.select_option('[id="category-input"]', value=category_id)

        # 9. Keywords (tags)
        if keywords:
            tags_input = page.locator('[id="tags-container"] input')
            await tags_input.click()
            for kw in keywords:
                await tags_input.type(kw)
                await page.keyboard.press("Enter")

        # 10. Navegar por los pasos: Siguiente x3
        for _ in range(3):
            await page.click('[id="next-button"]')
            await asyncio.sleep(1)

        # 11. Seleccionar "Programado"
        await page.click('[name="SCHEDULE"]')
        await page.wait_for_selector('[id="datepicker-trigger"]', timeout=10000)

        # 12. Ingresar fecha
        date_str = schedule_local.strftime("%d/%m/%Y")
        await page.fill('[id="datepicker-trigger"] input', date_str)
        await page.keyboard.press("Enter")

        # 13. Ingresar hora
        time_str = schedule_local.strftime("%H:%M")
        await page.fill('[id="timepicker-trigger"] input', time_str)
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)

        # 14. Guardar
        await page.click('[id="done-button"]')
        await page.wait_for_selector('ytcp-uploads-still-processing-dialog, [id="close-button"]', timeout=60000)

        await context.close()
    return "ok"
