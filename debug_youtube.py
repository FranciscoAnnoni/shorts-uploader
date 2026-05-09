"""
Script de debug para mapear el flujo de YouTube Studio paso a paso.
Corre con: python debug_youtube.py
Pausa en cada paso para que puedas inspeccionar el browser.
"""
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import SESSIONS_DIR, YT_STUDIO_URL

VIDEO_TEST = "/Users/FranciscoAnnoni/shorts-uploader/pending/"  # se pide por input

async def main():
    video_path = input("Path completo al video de prueba: ").strip()

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(SESSIONS_DIR / "youtube"),
            headless=False,
            channel="chrome",
            ignore_default_args=["--enable-automation"],
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        # PASO 1 — Navegar a YouTube Studio
        print("\n[PASO 1] Navegando a YouTube Studio...")
        await page.goto(YT_STUDIO_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        input(">>> Browser abierto en YouTube Studio. Presiona Enter para continuar al paso 2.")

        # PASO 2 — Buscar y clickear el boton Crear
        print("\n[PASO 2] Buscando boton 'Crear'...")
        # Imprimir todos los botones visibles para diagnostico
        buttons = await page.evaluate("""
            () => Array.from(document.querySelectorAll('button, [role=button], ytcp-button'))
                .filter(el => el.offsetParent !== null)
                .map(el => ({ tag: el.tagName, text: el.innerText?.trim().slice(0,50), id: el.id, aria: el.getAttribute('aria-label') }))
                .filter(el => el.text || el.aria)
        """)
        print("Botones visibles en la pagina:")
        for b in buttons[:20]:
            print(f"  tag={b['tag']} id={b['id']} aria='{b['aria']}' text='{b['text']}'")
        input(">>> Revisa los botones arriba. Presiona Enter para intentar click en 'Crear'.")

        # Intentar diferentes selectores para el boton Crear
        crear_selectors = [
            '#create-icon',
            'ytcp-button#create-icon',
            '[aria-label="Crear"]',
            '[aria-label="Create"]',
            'button:has-text("Crear")',
            '#upload-icon',
            'ytcp-icon-button[id="upload-icon"]',
        ]
        clicked_crear = False
        for sel in crear_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    print(f"  [OK] Selector encontrado: {sel}")
                    await el.click()
                    clicked_crear = True
                    break
            except Exception:
                pass

        if not clicked_crear:
            print("  [ERROR] No se encontro el boton Crear. Hacelo manualmente en el browser.")
        await asyncio.sleep(1)
        input(">>> Boton 'Crear' clickeado (o hacelo manual). Presiona Enter para ver el menu desplegable.")

        # PASO 3 — Ver opciones del menu desplegable
        print("\n[PASO 3] Buscando opciones del menu desplegable...")
        menu_items = await page.evaluate("""
            () => Array.from(document.querySelectorAll('tp-yt-paper-item, ytcp-paper-item, [role=menuitem], [role=option]'))
                .filter(el => el.offsetParent !== null)
                .map(el => ({ tag: el.tagName, text: el.innerText?.trim().slice(0,80), id: el.id }))
        """)
        print("Items del menu:")
        for item in menu_items:
            print(f"  tag={item['tag']} id={item['id']} text='{item['text']}'")
        input(">>> Revisa los items del menu arriba. Presiona Enter para intentar click en 'Subir videos'.")

        # Intentar diferentes selectores para Subir videos
        subir_selectors = [
            'tp-yt-paper-item:has-text("Subir")',
            'ytcp-paper-item:has-text("Subir")',
            '[role="menuitem"]:has-text("Subir")',
            'yt-formatted-string:has-text("Subir")',
        ]
        clicked_subir = False
        for sel in subir_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    print(f"  [OK] Selector encontrado: {sel}")
                    await el.click()
                    clicked_subir = True
                    break
            except Exception:
                pass

        if not clicked_subir:
            print("  [ERROR] No se encontro 'Subir videos'. Hacelo manualmente.")
        await asyncio.sleep(2)
        input(">>> 'Subir videos' clickeado. Presiona Enter para ver el dialog de upload.")

        # PASO 4 — Dialog de upload: buscar el file input
        print("\n[PASO 4] Buscando input de archivo...")
        file_inputs = await page.evaluate("""
            () => Array.from(document.querySelectorAll('input[type=file]'))
                .map(el => ({ id: el.id, name: el.name, accept: el.accept, hidden: el.style.display === 'none' }))
        """)
        print("File inputs encontrados:")
        for fi in file_inputs:
            print(f"  id={fi['id']} name={fi['name']} accept={fi['accept']} hidden={fi['hidden']}")

        input(">>> Presiona Enter para subir el video de prueba.")

        # Intentar subir el archivo
        try:
            file_chooser_triggered = False
            for sel in ['#select-files-button', 'input[type=file]', '[id="select-files-button"]']:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        if 'input' in sel:
                            await el.set_input_files(video_path)
                        else:
                            async with page.expect_file_chooser() as fc_info:
                                await el.click()
                            fc = await fc_info.value
                            await fc.set_files(video_path)
                        file_chooser_triggered = True
                        print(f"  [OK] Video subido via: {sel}")
                        break
                except Exception as e:
                    print(f"  [SKIP] {sel}: {e}")
        except Exception as e:
            print(f"  [ERROR] {e}")

        await asyncio.sleep(3)
        input(">>> Video en proceso de subida. Presiona Enter para inspeccionar el dialog de detalles.")

        # PASO 5 — Campo titulo
        print("\n[PASO 5] Buscando campo titulo...")
        title_elements = await page.evaluate("""
            () => Array.from(document.querySelectorAll('[id*="title"], [placeholder*="titulo"], [placeholder*="Titulo"], [placeholder*="title"]'))
                .filter(el => el.offsetParent !== null)
                .map(el => ({ tag: el.tagName, id: el.id, placeholder: el.placeholder, contenteditable: el.contentEditable }))
        """)
        print("Campos titulo encontrados:")
        for t in title_elements:
            print(f"  tag={t['tag']} id={t['id']} placeholder={t['placeholder']} contenteditable={t['contenteditable']}")

        input(">>> Fin del diagnostico. Podes cerrar el browser. El log de arriba nos dice que selectores usar.")
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
