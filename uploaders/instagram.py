import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import SESSIONS_DIR, META_BUSINESS_URL


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
    caption: str,
    schedule_dt: datetime,
) -> str:
    session_path = str(SESSIONS_DIR / "instagram")

    hour_12 = schedule_dt.hour % 12 or 12
    ampm = "PM" if schedule_dt.hour >= 12 else "AM"
    date_str = schedule_dt.strftime("%m/%d/%Y")

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
                    if (window._igLogActive) return;
                    window._igLogActive = true;
                    const log = (type, data) => {
                        const parts = Object.entries(data)
                            .filter(([, v]) => v)
                            .map(([k, v]) => k + '=' + String(v).substring(0, 60))
                            .join(' | ');
                        console.log('[IGBOT]', type, parts);
                    };
                    document.addEventListener('click', (e) => {
                        const el = e.target;
                        log('CLICK', {
                            tag: el.tagName,
                            id: el.id,
                            text: el.innerText?.trim()?.substring(0, 60),
                            ariaLabel: el.getAttribute('aria-label'),
                            role: el.getAttribute('role'),
                            class: el.className?.substring?.(0, 50),
                        });
                    }, true);
                    document.addEventListener('input', (e) => {
                        const el = e.target;
                        log('INPUT', {
                            tag: el.tagName,
                            id: el.id,
                            value: el.value?.substring?.(0, 80) || el.innerText?.substring?.(0, 80),
                            placeholder: el.getAttribute('placeholder'),
                            class: el.className?.substring?.(0, 40),
                        });
                    }, true);
                    document.addEventListener('change', (e) => {
                        const el = e.target;
                        log('CHANGE', { tag: el.tagName, id: el.id, value: el.value, name: el.getAttribute('name') });
                    }, true);
                }
            """)
        page.on("console", lambda msg: print(f"  [DOM] {msg.text}") if msg.text.startswith("[IGBOT]") else None)
        page.on("framenavigated", lambda _: asyncio.ensure_future(inject_logger()))

        # 1. Navegar a Meta Business Suite
        print("[IG] 1. Navegando a Meta Business Suite...")
        await page.goto(META_BUSINESS_URL, wait_until="domcontentloaded", timeout=60000)
        await inject_logger()
        await asyncio.sleep(5)

        # 2. Crear Reel
        print("[IG] 2. Abriendo Create Reel...")
        await page.locator('[role="button"]:has-text("Create reel")').first.click(timeout=20000)
        await asyncio.sleep(2)

        # 3. Add Video → file chooser nativo
        print("[IG] 3. Subiendo archivo...")
        async with page.expect_file_chooser(timeout=10000) as fc_info:
            await page.locator('[role="button"]:has-text("Add Video")').first.click(timeout=10000)
        fc = await fc_info.value
        await fc.set_files(video_path)
        await asyncio.sleep(3)

        # 4. Caption
        print("[IG] 4. Escribiendo caption...")
        caption_field = page.locator('div._5rpu[role="textbox"]').first
        await caption_field.wait_for(state="visible", timeout=120000)
        await asyncio.sleep(1)
        await caption_field.click()
        await asyncio.sleep(0.5)
        await page.keyboard.press("Control+a")
        await page.keyboard.type(caption)
        await asyncio.sleep(1)

        # 5. Next (Create → Edit) — Meta reemplaza el botón cuando el video procesa
        print("[IG] 5. Esperando Next habilitado (video procesando)...")
        try:
            await page.wait_for_function("""
                () => {
                    const btns = Array.from(document.querySelectorAll('[role="button"]'));
                    return btns.some(btn =>
                        btn.innerText?.trim() === 'Next'
                        && btn.getAttribute('aria-disabled') !== 'true'
                        && btn.getAttribute('tabindex') !== '-1'
                    );
                }
            """, timeout=120000)
        except Exception:
            print("[IG] 5. Timeout esperando Next — intentando igual...")
        print("[IG] 5. Clickeando Next (Create → Edit)...")
        clicked = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('[role="button"]'));
                for (const btn of btns) {
                    if (btn.innerText?.trim() === 'Next'
                        && btn.getAttribute('aria-disabled') !== 'true'
                        && btn.getAttribute('tabindex') !== '-1') {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        print(f"[IG] 5. Next clickeado: {clicked}")
        await asyncio.sleep(3)

        # 6. Next (Edit → Share)
        print("[IG] 6. Next (Edit → Share)...")
        clicked2 = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('[role="button"]'));
                for (const btn of btns) {
                    if (btn.innerText?.trim() === 'Next'
                        && btn.getAttribute('aria-disabled') !== 'true'
                        && btn.getAttribute('tabindex') !== '-1') {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        print(f"[IG] 6. Next clickeado: {clicked2}")
        await asyncio.sleep(4)

        # 7. Activar "Schedule" toggle
        print("[IG] 7. Activando Schedule...")
        schedule_toggle = page.locator('[role="button"]:has-text("Schedule")').first
        await schedule_toggle.wait_for(state="visible", timeout=30000)
        await schedule_toggle.click(timeout=10000)
        await asyncio.sleep(1)

        # 8. Fecha — usar placeholder estable en lugar de ID (IDs cambian entre sesiones)
        print(f"[IG] 8. Fecha {date_str}...")
        date_input = page.locator('input[placeholder="mm/dd/yyyy"]').first
        await date_input.wait_for(state="visible", timeout=15000)
        await date_input.click(timeout=5000)
        await asyncio.sleep(1)

        # 9. Seleccionar dia en el calendario
        print(f"[IG] 9. Seleccionando dia {schedule_dt.day}...")
        target_day_str = str(schedule_dt.day)
        for _ in range(3):
            day_clicked = await page.evaluate(f"""
                () => {{
                    const btns = Array.from(document.querySelectorAll('[role="button"]'));
                    for (const btn of btns) {{
                        const t = btn.innerText?.trim();
                        if (t !== '{target_day_str}') continue;
                        const r = btn.getBoundingClientRect();
                        if (r.height > 0 && r.height < 50) {{
                            btn.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """)
            if day_clicked:
                print(f"[IG] 9. Dia {target_day_str} clickeado")
                break
            await _click_if_visible(page, '[aria-label="Next month"], [aria-label="Mes siguiente"]', timeout=2000)
            await asyncio.sleep(0.5)
        await asyncio.sleep(1)

        # 10. Horas — usar aria-label estable
        print(f"[IG] 10. Hora {hour_12:02d}...")
        hours_input = page.locator('[role="spinbutton"][aria-label="hours"]').first
        await hours_input.click(click_count=3, timeout=5000)
        await page.keyboard.type(f"{hour_12:02d}")
        await asyncio.sleep(0.3)

        # 11. Minutos — usar aria-label estable
        print(f"[IG] 11. Minutos {schedule_dt.minute:02d}...")
        mins_input = page.locator('[role="spinbutton"][aria-label="minutes"]').first
        await mins_input.click(click_count=3, timeout=5000)
        await page.keyboard.type(f"{schedule_dt.minute:02d}")
        await asyncio.sleep(0.3)

        # 12. AM/PM — usar aria-label="meridiem"
        print(f"[IG] 12. {ampm}...")
        ampm_input = page.locator('[role="spinbutton"][aria-label="meridiem"]').first
        await ampm_input.click(timeout=5000)
        await asyncio.sleep(0.3)
        await page.keyboard.type(ampm)
        await asyncio.sleep(1)

        # 13. Confirmar Schedule — el submit NO tiene "Save as draft" como hermano (el radio sí)
        print("[IG] 13. Confirmando Schedule (submit)...")
        # Debug: listar todos los botones Schedule para entender la estructura
        schedule_btns_info = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('[role="button"]'));
                return btns
                    .filter(b => b.innerText?.trim() === 'Schedule')
                    .map((b, i) => ({
                        i,
                        ariaPressed: b.getAttribute('aria-pressed'),
                        tabindex: b.getAttribute('tabindex'),
                        style: (b.getAttribute('style') || '').substring(0, 60),
                        parentClass: (b.parentElement?.className || '').substring(0, 50),
                    }));
            }
        """)
        print(f"[IG] 13. Schedule buttons encontrados: {schedule_btns_info}")
        clicked13 = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('[role="button"]'));
                const scheduleBtns = btns.filter(b => b.innerText?.trim() === 'Schedule');
                for (const btn of scheduleBtns) {
                    // El radio option tiene "Save as draft" como hermano cercano
                    // El submit NO lo tiene
                    let el = btn;
                    let hasDraftSibling = false;
                    for (let depth = 0; depth < 6; depth++) {
                        if (!el.parentElement) break;
                        const sibs = Array.from(el.parentElement.querySelectorAll('[role="button"]'));
                        if (sibs.some(s => s.innerText?.trim() === 'Save as draft')) {
                            hasDraftSibling = true;
                            break;
                        }
                        el = el.parentElement;
                    }
                    if (!hasDraftSibling) {
                        btn.click();
                        return 'via-not-draft-sibling';
                    }
                }
                // Fallback: Previous está en el footer izquierdo, Schedule submit a la derecha
                const prevIdx = btns.findIndex(b => b.innerText?.trim() === 'Previous');
                if (prevIdx !== -1) {
                    for (let i = prevIdx + 1; i < btns.length; i++) {
                        if (btns[i].innerText?.trim() === 'Schedule') {
                            btns[i].click();
                            return 'via-previous-sibling';
                        }
                    }
                }
                return false;
            }
        """)
        print(f"[IG] 13. Submit método: {clicked13}")

        # Esperar respuesta de la página (éxito o error)
        await asyncio.sleep(6)
        page_text = await page.evaluate("() => document.body.innerText")
        # Buscar señales de éxito o error en el texto visible
        snippet = " | ".join(
            line.strip() for line in page_text.splitlines()
            if line.strip() and len(line.strip()) < 120
        )[:400]
        print(f"[IG] 13. Estado página post-submit: {snippet!r}")

        # 14. Cerrar modal si aparece (Dismiss en inglés, Descartar en español)
        print("[IG] 14. Cerrando modal...")
        dismissed = await _click_if_visible(page, '[role="button"]:has-text("Dismiss")', timeout=5000)
        if not dismissed:
            dismissed = await _click_if_visible(page, '[role="button"]:has-text("Descartar")', timeout=3000)
        if not dismissed:
            dismissed = await _click_if_visible(page, '[role="button"]:has-text("Done")', timeout=3000)
        print(f"[IG] 14. Modal cerrado: {dismissed}")
        await asyncio.sleep(2)

        await context.close()
    return "ok"
