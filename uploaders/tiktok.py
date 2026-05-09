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


async def upload(
    video_path: str,
    title: str,
    description: str,
    hashtags: str,
    schedule_dt: datetime,
) -> str:
    now_art = datetime.now(ART_TZ)
    dt_aware = ART_TZ.localize(schedule_dt) if schedule_dt.tzinfo is None else schedule_dt
    if dt_aware - now_art < timedelta(minutes=20):
        raise ValueError("TikTok requiere scheduling al menos 20 minutos en el futuro")

    caption = build_caption(title, description, hashtags)
    hour_str = f"{schedule_dt.hour:02d}"
    minute_str = f"{schedule_dt.minute:02d}"
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
            await page.wait_for_selector('input[type="file"]', timeout=10000)
        except Exception:
            print("[TT] 1b. Timeout esperando el form — puede ser redirect de login")
        await asyncio.sleep(2)

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

        # 6. Radio "Schedule"
        print("[TT] 6. Activando Schedule...")
        await page.evaluate("""
            const radios = Array.from(document.querySelectorAll('input[name="postSchedule"]'));
            const last = radios[radios.length - 1];
            if (last) {
                const circle = last.parentElement?.querySelector('.Radio__innerCircle');
                if (circle) circle.click();
                else last.click();
            }
        """)
        await asyncio.sleep(1)

        # 7. Permitir de nuevo
        await _click_if_visible(page, '[role="button"]:has-text("Permitir")', timeout=3000)

        # 8. Abrir datepicker
        print("[TT] 8. Abriendo datepicker...")
        await page.locator('div.TUXTextInputCore-trailingIconWrapper').first.click(timeout=5000)
        await asyncio.sleep(1)

        # 9. Hora (scroll picker 24h)
        print(f"[TT] 9. Hora {hour_str}:{minute_str}...")
        hour_option = page.locator(
            f'span.tiktok-timepicker-option-text.tiktok-timepicker-left:has-text("{hour_str}")'
        ).first
        await hour_option.click(timeout=5000)
        await asyncio.sleep(0.5)

        minute_option = page.locator(
            f'span.tiktok-timepicker-option-text.tiktok-timepicker-right:has-text("{minute_str}")'
        ).first
        await minute_option.click(timeout=5000)
        await asyncio.sleep(0.5)

        # 10. Día en el calendario
        print(f"[TT] 10. Día {schedule_dt.day}...")
        target_day = str(schedule_dt.day)
        for _ in range(3):
            day_clicked = await page.evaluate(f"""
                () => {{
                    const spans = Array.from(document.querySelectorAll('span'));
                    for (const span of spans) {{
                        const text = span.innerText?.trim();
                        if (text !== '{target_day}') continue;
                        const r = span.getBoundingClientRect();
                        if (r.height === 0) continue;
                        // Excluir spans del timepicker
                        if (span.className && span.className.includes('timepicker')) continue;
                        span.click();
                        return true;
                    }}
                    return false;
                }}
            """)
            if day_clicked:
                print(f"[TT] 10. Día {target_day} clickeado")
                break
            print(f"[TT] 10. Día {target_day} no encontrado, avanzando mes...")
            await _click_if_visible(
                page,
                '[aria-label="Next month"], [aria-label="Mes siguiente"], '
                'button.jsx-next-month, span.jsx-next-month',
                timeout=2000,
            )
            await asyncio.sleep(0.5)

        # Cerrar datepicker
        print("[TT] 10b. Cerrando datepicker...")
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
        await _click_if_visible(page, 'div.jsx-1566941760.main', timeout=2000)
        await asyncio.sleep(1)

        # 11. Post
        print("[TT] 11. Publicando...")
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

        await context.close()
    return "ok"
