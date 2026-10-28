import asyncio
from datetime import datetime, timedelta
import pytz
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import SESSIONS_DIR, TIKTOK_UPLOAD_URL, TIKTOK_CAPTION_MAX_CHARS

ART_TZ = pytz.timezone("America/Argentina/Buenos_Aires")


def build_caption(title: str, description: str, hashtags: str) -> str:
    caption = f"{title}\n\n{description}\n\n{hashtags}"
    return caption[:TIKTOK_CAPTION_MAX_CHARS]


async def _click_if_visible(page, selector, timeout=3000):
    try:
        el = page.locator(selector).first
        if await el.is_visible(timeout=timeout):
            await el.click()
            return True
    except Exception:
        pass
    return False


MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


async def _set_schedule(page, schedule_dt: datetime):
    # 6. Radio "Programacion"
    print("[TT] 6. Activando Schedule...")
    await page.locator('input[name="postSchedule"][value="schedule"]').evaluate(
        "e => (e.parentElement.querySelector('.Radio__innerCircle') || e).click()"
    )
    await _click_if_visible(page, '[role="button"]:has-text("Permitir")', timeout=3000)
    # dos desplegables: el primero es la fecha, el segundo la hora
    pickers = page.locator('.Picker__root.schedule-picker')
    await pickers.nth(1).wait_for(state="visible", timeout=10000)

    # 7. Fecha: cada dia es un boton con aria-label "miercoles, 28 de octubre de 2026"
    mes = MESES_ES[schedule_dt.month - 1]
    print(f"[TT] 7. Fecha {schedule_dt:%Y-%m-%d}...")
    await pickers.nth(0).click()
    # con la coma adelante: "8 de octubre" tambien es el final de "28 de octubre"
    day_label = f", {schedule_dt.day} de {mes} de {schedule_dt.year}"
    day_btn = page.locator(f'button.DatePicker__day[aria-label$="{day_label}"][data-outside="false"]')
    for _ in range(3):
        if await day_btn.count():
            break
        await page.locator('button.DatePicker__nav[aria-label="Next month"]').first.click(timeout=5000)
    await day_btn.first.click(timeout=5000)

    # 8. Hora: columnas de botones con aria-label "Hours 21" / "Minutes 30"
    print(f"[TT] 8. Hora {schedule_dt:%H:%M}...")
    await pickers.nth(1).click()
    await page.locator(f'button.TimePicker__item[aria-label="Hours {schedule_dt:%H}"]').click(timeout=5000)
    await page.locator(f'button.TimePicker__item[aria-label="Minutes {schedule_dt:%M}"]').click(timeout=5000)
    await page.keyboard.press("Escape")
    await asyncio.sleep(0.5)

    # 9. Verificar lo que muestran los dos desplegables ("27 oct 2026", "21:30")
    shown = [t.strip() for t in await pickers.locator('.Picker__value').all_inner_texts()]
    expected = [f"{schedule_dt.day} {mes[:3]}", str(schedule_dt.year), f"{schedule_dt:%H:%M}"]
    if len(shown) != 2 or not (
        shown[0].startswith(expected[0]) and shown[0].endswith(expected[1]) and shown[1] == expected[2]
    ):
        shot = SESSIONS_DIR.parent / "debug_tiktok_date.png"
        await page.screenshot(path=str(shot))
        raise RuntimeError(f"TikTok muestra {shown} en vez de {expected} (captura: {shot})")
    print(f"[TT] 9. Fecha y hora OK: {shown}")


async def upload(
    video_path: str,
    title: str,
    description: str,
    hashtags: str,
    schedule_dt: datetime,
    on_confirmed=None,
) -> str:
    if schedule_dt is not None:
        dt_aware = ART_TZ.localize(schedule_dt) if schedule_dt.tzinfo is None else schedule_dt
        if dt_aware - datetime.now(ART_TZ) < timedelta(minutes=20):
            raise ValueError("TikTok requiere scheduling al menos 20 minutos en el futuro")

    caption = build_caption(title, description, hashtags)
    session_path = str(SESSIONS_DIR / "tiktok")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            session_path,
            headless=False,
            channel="chrome",
            ignore_default_args=["--enable-automation"],
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        async def inject_logger():
            await page.evaluate("""
                () => {
                    if (window._ttLogActive) return;
                    window._ttLogActive = true;
                    const log = (type, data) => {
                        const parts = Object.entries(data)
                            .filter(([, v]) => v)
                            .map(([k, v]) => k + '=' + String(v).substring(0, 60))
                            .join(' | ');
                        console.log('[TTBOT]', type, parts);
                    };
                    document.addEventListener('click', (e) => {
                        const el = e.target;
                        log('CLICK', {
                            tag: el.tagName,
                            id: el.id,
                            text: el.innerText?.trim()?.substring(0, 60),
                            dataE2e: el.getAttribute('data-e2e'),
                            class: el.className?.substring?.(0, 50),
                            role: el.getAttribute('role'),
                        });
                    }, true);
                    document.addEventListener('input', (e) => {
                        const el = e.target;
                        log('INPUT', {
                            tag: el.tagName,
                            id: el.id,
                            value: el.value?.substring?.(0, 80) || el.innerText?.substring?.(0, 80),
                            dataE2e: el.getAttribute('data-e2e'),
                            class: el.className?.substring?.(0, 40),
                        });
                    }, true);
                    document.addEventListener('change', (e) => {
                        const el = e.target;
                        log('CHANGE', { tag: el.tagName, id: el.id, value: el.value, name: el.getAttribute('name') });
                    }, true);
                }
            """)
        page.on("console", lambda msg: print(f"  [DOM] {msg.text}") if msg.text.startswith("[TTBOT]") else None)
        page.on("framenavigated", lambda _: asyncio.ensure_future(inject_logger()))

        # 1. Navegar al creator center
        print("[TT] 1. Navegando a TikTok Creator Center...")
        await page.goto(TIKTOK_UPLOAD_URL, wait_until="domcontentloaded", timeout=60000)
        await inject_logger()
        # Esperar a que la página cargue completamente (maneja redirect de login)
        print("[TT] 1b. Esperando que cargue el form de upload...")
        try:
            await page.wait_for_selector('input[type="file"]', state="attached", timeout=30000)
        except Exception:
            print("[TT] 1b. Timeout esperando el form — puede ser redirect de login")

        # 2. Subir archivo
        print("[TT] 2. Subiendo archivo...")
        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(video_path)
        await asyncio.sleep(5)

        # 3. Remover joyride overlay
        print("[TT] 3. Removiendo overlays...")
        await page.evaluate("document.querySelector('#react-joyride-portal')?.remove()")
        await asyncio.sleep(0.5)

        # 4. Caption
        print("[TT] 4. Escribiendo caption...")
        caption_field = page.locator('div.public-DraftEditor-content').first
        await caption_field.wait_for(state="visible", timeout=30000)
        # Limpiar el editor Draft.js via JS antes de escribir
        await page.evaluate("""
            () => {
                const editor = document.querySelector('div.public-DraftEditor-content');
                if (!editor) return;
                // Seleccionar todo el contenido del editor y borrarlo
                editor.focus();
                const sel = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(editor);
                sel.removeAllRanges();
                sel.addRange(range);
            }
        """)
        await asyncio.sleep(0.3)
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.3)
        await caption_field.click()
        await asyncio.sleep(0.3)
        await page.keyboard.type(caption, delay=20)
        await asyncio.sleep(1)

        # 5. "Permitir" popup
        await _click_if_visible(page, '[role="button"]:has-text("Permitir")', timeout=3000)

        # 6-10. Cuando publicar. schedule_dt None = publicar ya (radio "Ahora",
        # que viene marcado por defecto).
        if schedule_dt is None:
            print("[TT] 6. Publicar ahora...")
            await page.locator('input[name="postSchedule"][value="post_now"]').evaluate(
                "e => e.checked || (e.parentElement.querySelector('.Radio__innerCircle') || e).click()"
            )
        else:
            await _set_schedule(page, schedule_dt)

        # 11. Post
        print("[TT] 11. Publicando...")
        # TikTok deshabilita el boton mientras procesa el video o corre comprobaciones
        try:
            await page.wait_for_selector(
                '[data-e2e="post_video_button"][data-disabled="false"]', timeout=180000
            )
        except Exception:
            shot = SESSIONS_DIR.parent / "debug_tiktok_post.png"
            await page.screenshot(path=str(shot), full_page=True)
            raise RuntimeError(f"Boton Programar de TikTok sigue deshabilitado tras 3 min (captura: {shot})")
        await page.locator('[data-e2e="post_video_button"]').first.click(timeout=15000)
        await asyncio.sleep(3)

        # 11b. Modal de copyright pendiente — "Publicar ahora"
        try:
            modal = page.locator('.TUXModal')
            if await modal.is_visible(timeout=4000):
                print("[TT] 11b. Modal de copyright detectado, confirmando...")
                await page.locator('.TUXButton--primary').first.click(timeout=5000)
                await asyncio.sleep(2)
        except Exception:
            pass

        # 12. Confirmacion: TikTok sale del formulario de subida (va a la lista de
        # contenido). Si el boton sigue ahi, la programacion no se envio.
        print("[TT] 12. Esperando confirmacion...")
        try:
            await page.locator('[data-e2e="post_video_button"]').wait_for(state="detached", timeout=90000)
        except Exception:
            shot = SESSIONS_DIR.parent / "debug_tiktok_confirm.png"
            await page.screenshot(path=str(shot))
            raise RuntimeError(f"TikTok no confirmo la programacion (captura: {shot})")
        print(f"[TT] 12. Confirmado. URL: {page.url}")
        if on_confirmed:
            on_confirmed()  # avisar ya: el cierre del browser a veces se cuelga

        print("[TT] 13. Cerrando browser...")
        # el video ya esta confirmado: si el browser no cierra, no colgar la app
        try:
            await asyncio.wait_for(context.close(), timeout=20)
            print("[TT] 13. Browser cerrado.")
        except asyncio.TimeoutError:
            print("[TT] 13. El browser no cerro en 20 s, sigo igual.")
    return "ok"
