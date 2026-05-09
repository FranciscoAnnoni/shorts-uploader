import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import SESSIONS_DIR, YT_STUDIO_URL

CATEGORY_NAMES = {
    "27": "Educación",
    "28": "Ciencia y tecnología",
}

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
    keywords: list[str],
    language: str,
    category_id: str,
    schedule_dt: datetime,
) -> str:
    session_path = str(SESSIONS_DIR / "youtube")
    full_description = f"{description}\n\n{hashtags}"
    schedule_local = schedule_dt
    tags_str = ", ".join(keywords)
    category_name = CATEGORY_NAMES.get(category_id, "Educación")

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

        # Inyectar logger de eventos para debug
        async def inject_logger():
            await page.evaluate("""
                () => {
                    if (window._ytLogActive) return;
                    window._ytLogActive = true;
                    const log = (type, data) => {
                        const parts = Object.entries(data)
                            .filter(([, v]) => v)
                            .map(([k, v]) => k + '=' + String(v).substring(0, 60))
                            .join(' | ');
                        console.log('[YTBOT]', type, parts);
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
                            value: el.value,
                            placeholder: el.getAttribute('placeholder'),
                        });
                    }, true);
                    document.addEventListener('change', (e) => {
                        const el = e.target;
                        log('CHANGE', { tag: el.tagName, id: el.id, value: el.value });
                    }, true);
                }
            """)
        page.on("console", lambda msg: print(f"  [DOM] {msg.text}") if msg.text.startswith("[YTBOT]") else None)
        page.on("framenavigated", lambda _: asyncio.ensure_future(inject_logger()))

        print("[YT] 1. Navegando a YouTube Studio...")
        await page.goto(YT_STUDIO_URL, wait_until="domcontentloaded", timeout=60000)
        await inject_logger()
        await asyncio.sleep(3)

        print("[YT] 2. Crear → Subir vídeos")
        await page.click('[aria-label="Crear"]', timeout=15000)
        await asyncio.sleep(1)
        await page.click('#text-item-0', timeout=10000)
        await asyncio.sleep(2)

        print("[YT] 3. Subiendo archivo...")
        file_input = page.locator('[name="Filedata"]').first
        await file_input.set_input_files(video_path)

        print("[YT] 4. Esperando campo título...")
        await page.wait_for_selector('[id="title-textarea"] #textbox', timeout=60000)
        await asyncio.sleep(2)

        print("[YT] 5. Escribiendo título...")
        title_field = page.locator('[id="title-textarea"] #textbox')
        await title_field.click(click_count=3)
        await title_field.fill(title)
        await asyncio.sleep(1)

        print("[YT] 6. Escribiendo descripción...")
        desc_field = page.locator('[id="description-textarea"] #textbox')
        await desc_field.click()
        await desc_field.fill(full_description)
        await asyncio.sleep(1)

        print("[YT] 7. No para niños...")
        not_kids = await page.evaluate("""
            () => {
                const buttons = document.querySelectorAll('ytcp-radio-button, tp-yt-paper-radio-button');
                for (const btn of buttons) {
                    const text = (btn.innerText || btn.textContent || '').trim();
                    if (text.startsWith('No') && text.includes('ni')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        if not not_kids:
            await page.locator('#offRadio').nth(1).click()
        await asyncio.sleep(1)

        print("[YT] 8. Configuración avanzada...")
        await _click_if_visible(page, '[aria-label="Mostrar configuración avanzada"]', timeout=5000)
        await asyncio.sleep(2)

        print("[YT] 9. Tags...")
        tags_input = page.locator('[aria-label="Etiquetas"]').first
        if await tags_input.is_visible(timeout=5000):
            await tags_input.click()
            await tags_input.fill(tags_str)
            await page.keyboard.press("Tab")
            await asyncio.sleep(1)

        # 10. Idioma del vídeo
        print("[YT] 10. Idioma...")
        lang_opened = await page.evaluate("""
            () => {
                const input = document.querySelector('ytcp-form-language-input');
                if (!input) return false;
                const trigger = input.querySelector('ytcp-dropdown-trigger');
                if (trigger && trigger.offsetParent) { trigger.click(); return true; }
                return false;
            }
        """)
        if lang_opened:
            await asyncio.sleep(1)
            clicked = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('tp-yt-paper-item');
                    for (const item of items) {
                        const r = item.getBoundingClientRect();
                        if (r.height > 0 && item.innerText?.trim().startsWith('Español')) {
                            item.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            if not clicked:
                await page.keyboard.press("Escape")
            await asyncio.sleep(1)

        # 11. Categoría
        print("[YT] 11. Categoría...")
        cat_opened = await page.evaluate("""
            () => {
                // Buscar el elemento con texto exacto "Categoría" y subir hasta encontrar el trigger
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                let node;
                while (node = walker.nextNode()) {
                    if (node.textContent.trim() === 'Categoría') {
                        let el = node.parentElement;
                        for (let i = 0; i < 8; i++) {
                            if (!el) break;
                            const trigger = el.querySelector('ytcp-dropdown-trigger');
                            if (trigger && trigger.offsetParent) { trigger.click(); return true; }
                            el = el.parentElement;
                        }
                    }
                }
                return false;
            }
        """)
        if cat_opened:
            await asyncio.sleep(1)
            clicked = await page.evaluate(f"""
                () => {{
                    const items = document.querySelectorAll('tp-yt-paper-item');
                    for (const item of items) {{
                        const r = item.getBoundingClientRect();
                        if (r.height > 0 && item.innerText?.trim().includes('{category_name}')) {{
                            item.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """)
            if not clicked:
                await page.keyboard.press("Escape")
            await asyncio.sleep(1)

        # 12. Siguiente → página de elementos/idoneidad
        print("[YT] 12. Siguiente (detalles → elementos)...")
        await page.click('[aria-label="Siguiente"]', timeout=15000)
        await asyncio.sleep(2)

        # 13. Idoneidad para anuncios (siempre marcar)
        print("[YT] 13. Ads/idoneidad...")
        ads_checkbox = page.locator('#checkbox-container').first
        if await ads_checkbox.is_visible(timeout=5000):
            await ads_checkbox.click()
            await asyncio.sleep(1)
        await _click_if_visible(page, '[aria-label="Enviar calificación"]', timeout=5000)
        await asyncio.sleep(1)

        # 14. Siguiente → verificaciones (puede aparecer error de licencia, se ignora)
        print("[YT] 14. Siguiente (elementos → verificaciones)...")
        await page.click('[aria-label="Siguiente"]', timeout=15000)
        await asyncio.sleep(2)

        # Si aparece dialog de error de licencia, avanzar igual
        if await page.locator('ytcr-license-activation-error-dialog, ytcp-confirmation-dialog#error-dialog').first.is_visible(timeout=3000):
            await _click_if_visible(page, '[aria-label="Siguiente"]', timeout=5000)
            await asyncio.sleep(1)

        # 15. Siguiente desde verificaciones — esperar que no esté disabled
        print("[YT] 15. Siguiente (verificaciones)...")
        next_btn = page.locator('[aria-label="Siguiente"]').first
        for _ in range(30):  # hasta 60s mientras checks corren
            if await next_btn.get_attribute('aria-disabled') != 'true':
                break
            await asyncio.sleep(2)
        await next_btn.click(timeout=15000)
        await asyncio.sleep(3)

        # 16. Siguiente extra — siempre necesario para llegar a visibilidad
        print("[YT] 16. Siguiente → visibilidad...")
        try:
            await page.wait_for_selector('#visibility-title', timeout=4000)
            print("[YT] 16. Ya en visibilidad.")
        except Exception:
            await page.click('[aria-label="Siguiente"]', timeout=10000)
            await asyncio.sleep(3)

        # 17. Confirmar página de visibilidad
        print("[YT] 17. Esperando visibilidad...")
        await page.wait_for_selector('#visibility-title', timeout=30000)
        await asyncio.sleep(2)

        # 17b. Expandir sección "Programar" SOLO si está colapsada
        print("[YT] 17b. Verificando sección Programar...")
        expand_attr = await page.locator('#second-container-expand-button').get_attribute('hidden')
        if expand_attr is None:
            print("[YT] 17b. Colapsada — expandiendo...")
            await page.locator('#second-container-expand-button').click()
            await asyncio.sleep(1)
        else:
            print("[YT] 17b. Ya expandida.")

        # 18. Fecha — esperar que datepicker sea visible y clickear
        print("[YT] 18. Fecha...")
        target_day = schedule_local.day
        date_trigger = page.locator('#datepicker-trigger').first
        await date_trigger.wait_for(state="visible", timeout=8000)
        await date_trigger.click()
        await asyncio.sleep(1)
        for _ in range(3):
            day_clicked = await page.evaluate(f"""
                () => {{
                    const cells = document.querySelectorAll('[class*="calendar"] td, [class*="calendar"] [class*="day"]');
                    for (const cell of cells) {{
                        if (cell.innerText?.trim() === '{target_day}' && cell.offsetParent) {{
                            cell.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """)
            if day_clicked:
                break
            await _click_if_visible(page, '[aria-label="Mes siguiente"], [aria-label="Next month"]', timeout=3000)
            await asyncio.sleep(1)
        # Cerrar calendario — Escape + click fuera + esperar que desaparezca el overlay
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
        try:
            await page.wait_for_selector(
                'tp-yt-iron-overlay-backdrop.opened', state='hidden', timeout=4000
            )
        except Exception:
            # Forzar cierre clickeando fuera del picker
            await page.mouse.click(200, 200)
            await asyncio.sleep(0.5)
        await asyncio.sleep(0.5)
        trigger_text = await date_trigger.inner_text()
        print(f"[YT] 18. Fecha: {trigger_text.strip()!r}")

        # 19. Hora — el input abre un dropdown con opciones cada 15 min
        # Formato del dropdown: "H:MM" sin zero-pad en la hora
        time_display = f"{schedule_local.hour}:{schedule_local.minute:02d}"
        print(f"[YT] 19. Hora ({time_display})...")
        time_field = page.locator('#time-of-day-container input').first
        await time_field.wait_for(state="visible", timeout=5000)
        await time_field.click()
        await asyncio.sleep(0.5)
        # Seleccionar del dropdown por texto exacto
        clicked = await page.evaluate(f"""
            () => {{
                const items = document.querySelectorAll('tp-yt-paper-item, [role="option"]');
                for (const item of items) {{
                    const r = item.getBoundingClientRect();
                    if (r.height > 0 && item.innerText?.trim() === '{time_display}') {{
                        item.click();
                        return true;
                    }}
                }}
                return false;
            }}
        """)
        if not clicked:
            print(f"[YT] 19. Opción {time_display!r} no encontrada en dropdown, tipeando...")
            await time_field.click(click_count=3)
            await page.keyboard.type(time_display)
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
        # Esperar que el overlay del dropdown cierre
        try:
            await page.wait_for_selector(
                'tp-yt-iron-overlay-backdrop.opened', state='hidden', timeout=4000
            )
        except Exception:
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
        actual_val = await time_field.input_value()
        print(f"[YT] 19. Hora: {actual_val!r}")

        # 20. Botón Programar — esperar que no haya overlay bloqueando
        print("[YT] 20. Programar...")
        try:
            await page.wait_for_selector(
                'tp-yt-iron-overlay-backdrop.opened', state='hidden', timeout=5000
            )
        except Exception:
            pass
        await page.click('[aria-label="Programar"]', timeout=15000)
        await asyncio.sleep(3)

        # 21. Warning de idoneidad para anuncios
        await _click_if_visible(page, '[aria-label="Entendido"]', timeout=5000)
        await asyncio.sleep(1)

        # 22. Dialog de compartir → cerrar
        await _click_if_visible(page, '[aria-label="Cerrar"]', timeout=8000)
        await asyncio.sleep(2)

        await context.close()
    return "ok"
