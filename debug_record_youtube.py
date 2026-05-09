"""
Recorder para el flujo de scheduling en YouTube Studio.
Hace el proceso completo vos manualmente y guarda todos los eventos.
Uso: python debug_record_youtube.py
"""
import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import SESSIONS_DIR, YT_STUDIO_URL


async def main():
    session_path = str(SESSIONS_DIR / "youtube")

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

        await page.goto(YT_STUDIO_URL, wait_until="domcontentloaded", timeout=60000)

        await page.evaluate("""
            () => {
                window._ytLog = [];
                const log = (type, data) => {
                    const entry = { t: Date.now(), type, ...data };
                    window._ytLog.push(entry);
                };

                document.addEventListener('click', (e) => {
                    const el = e.target;
                    log('CLICK', {
                        tag: el.tagName,
                        id: el.id || null,
                        class: (el.className?.substring?.(0, 80)) || null,
                        text: (el.innerText?.trim()?.substring?.(0, 80)) || null,
                        name: el.getAttribute?.('name') || null,
                        ariaLabel: el.getAttribute?.('aria-label') || null,
                        role: el.getAttribute?.('role') || null,
                        dataE2e: el.getAttribute?.('data-e2e') || null,
                    });
                }, true);

                document.addEventListener('input', (e) => {
                    const el = e.target;
                    log('INPUT', {
                        tag: el.tagName,
                        id: el.id || null,
                        value: (el.value?.substring?.(0, 100)) || null,
                        name: el.getAttribute?.('name') || null,
                        placeholder: el.getAttribute?.('placeholder') || null,
                        type: el.getAttribute?.('type') || null,
                    });
                }, true);

                document.addEventListener('change', (e) => {
                    const el = e.target;
                    log('CHANGE', {
                        tag: el.tagName,
                        id: el.id || null,
                        value: (el.value?.substring?.(0, 100)) || null,
                        name: el.getAttribute?.('name') || null,
                    });
                }, true);
            }
        """)

        print("Recorder activo. Hace el proceso COMPLETO manualmente:")
        print("  1. Crear → Subir vídeo → cargar archivo")
        print("  2. Llenar titulo, descripcion, hashtags")
        print("  3. No para niños")
        print("  4. Configuración avanzada → idioma, categoría")
        print("  5. Siguiente x3 hasta Visibilidad")
        print("  6. Setear fecha y hora en el scheduler")
        print("  7. Click Programar")
        print("  8. Cerrar dialogs")
        input("\nPresioná Enter cuando hayas completado TODA la subida...")

        logs = await page.evaluate("() => window._ytLog || []")
        await context.close()

    with open("debug_youtube_log.json", "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
    print(f"\nLog guardado: debug_youtube_log.json ({len(logs)} eventos)")


if __name__ == "__main__":
    asyncio.run(main())
