"""
Abre YouTube Studio y registra cada interaccion manual.
Uso: python debug_record.py
Hace todo vos en el browser. Cuando termines presiona Enter en la terminal.
"""
import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import SESSIONS_DIR, YT_STUDIO_URL

INJECT_JS = """
window.__log = [];

function getSelector(el) {
    if (!el || el === document.body) return 'body';
    if (el.id) return '#' + el.id;
    if (el.getAttribute('aria-label')) return `[aria-label="${el.getAttribute('aria-label')}"]`;
    if (el.getAttribute('name')) return `[name="${el.getAttribute('name')}"]`;
    if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
    const text = el.innerText?.trim().slice(0, 40);
    if (text) return `${el.tagName.toLowerCase()}:has-text("${text}")`;
    return el.tagName.toLowerCase() + (el.className ? '.' + el.className.split(' ')[0] : '');
}

// Registrar clicks
document.addEventListener('click', (e) => {
    const el = e.target;
    const closest = el.closest('button, [role=button], input, a, tp-yt-paper-item, ytcp-paper-item, ytcp-button, ytcp-icon-button') || el;
    const entry = {
        type: 'CLICK',
        selector: getSelector(closest),
        tag: closest.tagName,
        id: closest.id || '',
        aria: closest.getAttribute('aria-label') || '',
        text: closest.innerText?.trim().slice(0, 60) || '',
        time: new Date().toLocaleTimeString()
    };
    window.__log.push(entry);
    console.log('ACTION:' + JSON.stringify(entry));
}, true);

// Registrar inputs de texto
document.addEventListener('input', (e) => {
    const el = e.target;
    const entry = {
        type: 'INPUT',
        selector: getSelector(el),
        tag: el.tagName,
        id: el.id || '',
        value: (el.value || el.innerText || '').slice(0, 80),
        time: new Date().toLocaleTimeString()
    };
    window.__log.push(entry);
    console.log('ACTION:' + JSON.stringify(entry));
}, true);

// Detectar nuevos dialogs/modales
const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
        for (const node of m.addedNodes) {
            if (node.nodeType === 1) {
                const tag = node.tagName?.toLowerCase() || '';
                if (tag.includes('dialog') || tag.includes('modal') || tag.includes('paper-dialog') || node.getAttribute?.('role') === 'dialog') {
                    const entry = { type: 'DIALOG_OPEN', tag, id: node.id || '', time: new Date().toLocaleTimeString() };
                    window.__log.push(entry);
                    console.log('ACTION:' + JSON.stringify(entry));
                }
            }
        }
    }
});
observer.observe(document.body, { childList: true, subtree: true });

console.log('ACTION:' + JSON.stringify({type: 'READY', time: new Date().toLocaleTimeString()}));
"""

async def main():
    print("="*60)
    print("GRABADOR DE SESION — YouTube Studio")
    print("="*60)
    print("1. Se va a abrir Chrome con tu sesion de YouTube Studio")
    print("2. Hace el flujo completo a mano:")
    print("   - Click en el icono de subida (camara/+)")
    print("   - Selecciona 'Subir videos'")
    print("   - Elige el archivo de video")
    print("   - Completa titulo, descripcion")
    print("   - Hace click en 'No para ninos'")
    print("   - Mas opciones, idioma, categoria")
    print("   - Siguiente x3")
    print("   - Programado, fecha/hora")
    print("   - Guardar")
    print("3. Cuando termines presiona Enter en esta terminal")
    print("="*60)
    input("Presiona Enter para abrir el browser...")

    actions = []

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

        # Capturar logs del browser
        def handle_console(msg):
            text = msg.text
            if text.startswith("ACTION:"):
                try:
                    data = json.loads(text[7:])
                    actions.append(data)
                    t = data.get('time', '')
                    if data['type'] == 'CLICK':
                        print(f"  [{t}] CLICK   → {data['selector']}  (aria: '{data['aria']}' text: '{data['text']}')")
                    elif data['type'] == 'INPUT':
                        print(f"  [{t}] INPUT   → {data['selector']}  value: '{data['value']}'")
                    elif data['type'] == 'DIALOG_OPEN':
                        print(f"  [{t}] DIALOG  → <{data['tag']} id='{data['id']}'>")
                    elif data['type'] == 'READY':
                        print(f"  [{t}] Listener listo en la pagina")
                except Exception:
                    pass

        page.on("console", handle_console)

        # Re-inyectar el listener en cada navegacion
        async def inject_on_load(p_frame):
            try:
                await page.evaluate(INJECT_JS)
            except Exception:
                pass

        page.on("domcontentloaded", inject_on_load)

        await page.goto(YT_STUDIO_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)
        await page.evaluate(INJECT_JS)

        print("\n[OK] Browser abierto. Hace el flujo completo en el browser.")
        print("     Cada accion que hagas aparece logueada arriba en tiempo real.")
        print()
        input("Presiona Enter cuando termines el flujo completo...")

        await context.close()

    # Resumen final
    print("\n" + "="*60)
    print("RESUMEN DE ACCIONES GRABADAS")
    print("="*60)
    for i, a in enumerate(actions):
        if a['type'] == 'CLICK':
            print(f"[{i+1}] CLICK   {a['selector']}")
            if a['aria']:
                print(f"       aria-label: '{a['aria']}'")
            if a['text']:
                print(f"       text: '{a['text']}'")
        elif a['type'] == 'INPUT':
            print(f"[{i+1}] INPUT   {a['selector']} = '{a['value']}'")
        elif a['type'] == 'DIALOG_OPEN':
            print(f"[{i+1}] DIALOG  <{a['tag']} id='{a['id']}'>")

    # Guardar a archivo
    output_file = "debug_youtube_log.json"
    with open(output_file, "w") as f:
        json.dump(actions, f, indent=2)
    print(f"\nLog completo guardado en: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
