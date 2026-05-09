"""
Abre Meta Business Suite y registra cada interaccion manual.
Uso: python debug_record_instagram.py
Hace todo vos en el browser. Cuando termines presiona Enter en la terminal.
"""
import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import SESSIONS_DIR, META_BUSINESS_URL

INJECT_JS = """
window.__log = [];

function getSelector(el) {
    if (!el || el === document.body) return 'body';
    if (el.id) return '#' + el.id;
    if (el.getAttribute('aria-label')) return `[aria-label="${el.getAttribute('aria-label')}"]`;
    if (el.getAttribute('name')) return `[name="${el.getAttribute('name')}"]`;
    if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
    if (el.getAttribute('role')) {
        const text = el.innerText?.trim().slice(0, 40);
        if (text) return `[role="${el.getAttribute('role')}"]:has-text("${text}")`;
    }
    const text = el.innerText?.trim().slice(0, 40);
    if (text) return `${el.tagName.toLowerCase()}:has-text("${text}")`;
    return el.tagName.toLowerCase() + (el.className ? '.' + el.className.split(' ')[0] : '');
}

function getFullInfo(el) {
    return {
        tag: el.tagName,
        id: el.id || '',
        aria: el.getAttribute('aria-label') || '',
        role: el.getAttribute('role') || '',
        testid: el.getAttribute('data-testid') || '',
        name: el.getAttribute('name') || '',
        placeholder: el.getAttribute('placeholder') || '',
        type: el.getAttribute('type') || '',
        classes: el.className?.toString().slice(0, 80) || '',
        text: el.innerText?.trim().slice(0, 60) || '',
    };
}

document.addEventListener('click', (e) => {
    const el = e.target;
    const closest = el.closest('button, [role=button], input, a, [role=tab], [role=menuitem], [role=option], div[tabindex]') || el;
    const info = getFullInfo(closest);
    const entry = {
        type: 'CLICK',
        selector: getSelector(closest),
        ...info,
        time: new Date().toLocaleTimeString()
    };
    window.__log.push(entry);
    console.log('ACTION:' + JSON.stringify(entry));
}, true);

document.addEventListener('input', (e) => {
    const el = e.target;
    const info = getFullInfo(el);
    const entry = {
        type: 'INPUT',
        selector: getSelector(el),
        ...info,
        value: (el.value || el.innerText || '').slice(0, 80),
        time: new Date().toLocaleTimeString()
    };
    window.__log.push(entry);
    console.log('ACTION:' + JSON.stringify(entry));
}, true);

document.addEventListener('change', (e) => {
    const el = e.target;
    if (el.tagName === 'INPUT' || el.tagName === 'SELECT') {
        const info = getFullInfo(el);
        const entry = {
            type: 'CHANGE',
            selector: getSelector(el),
            ...info,
            value: (el.value || '').slice(0, 80),
            time: new Date().toLocaleTimeString()
        };
        window.__log.push(entry);
        console.log('ACTION:' + JSON.stringify(entry));
    }
}, true);

const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
        for (const node of m.addedNodes) {
            if (node.nodeType === 1) {
                const tag = node.tagName?.toLowerCase() || '';
                if (tag.includes('dialog') || tag.includes('modal') || node.getAttribute?.('role') === 'dialog') {
                    const entry = {
                        type: 'DIALOG_OPEN',
                        tag,
                        id: node.id || '',
                        aria: node.getAttribute?.('aria-label') || '',
                        testid: node.getAttribute?.('data-testid') || '',
                        time: new Date().toLocaleTimeString()
                    };
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
    print("GRABADOR DE SESION — Meta Business Suite (Instagram Reels)")
    print("="*60)
    print("1. Se abre Chrome con tu sesion de Meta Business Suite")
    print("2. Hace el flujo completo a mano:")
    print("   - Click en el boton de crear publicacion")
    print("   - Seleccionar tipo: Reel")
    print("   - Subir el video")
    print("   - Esperar procesamiento")
    print("   - Escribir caption")
    print("   - Cambiar a 'Programar' (en vez de 'Publicar ahora')")
    print("   - Elegir fecha y hora")
    print("   - Confirmar / Guardar")
    print("3. Cuando termines presiona Enter en esta terminal")
    print("="*60)
    input("Presiona Enter para abrir el browser...")

    actions = []

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(SESSIONS_DIR / "instagram"),
            headless=False,
            channel="chrome",
            ignore_default_args=["--enable-automation"],
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        def handle_console(msg):
            text = msg.text
            if text.startswith("ACTION:"):
                try:
                    data = json.loads(text[7:])
                    actions.append(data)
                    t = data.get('time', '')
                    if data['type'] == 'CLICK':
                        aria = data.get('aria', '')
                        testid = data.get('testid', '')
                        txt = data.get('text', '')
                        role = data.get('role', '')
                        print(f"  [{t}] CLICK   → {data['selector']}")
                        if aria:   print(f"           aria-label: '{aria}'")
                        if testid: print(f"           data-testid: '{testid}'")
                        if role:   print(f"           role: '{role}'")
                        if txt:    print(f"           text: '{txt}'")
                    elif data['type'] == 'INPUT':
                        print(f"  [{t}] INPUT   → {data['selector']}  value: '{data.get('value', '')}'")
                        if data.get('placeholder'): print(f"           placeholder: '{data['placeholder']}'")
                    elif data['type'] == 'CHANGE':
                        print(f"  [{t}] CHANGE  → {data['selector']}  value: '{data.get('value', '')}'")
                    elif data['type'] == 'DIALOG_OPEN':
                        print(f"  [{t}] DIALOG  → <{data['tag']} id='{data['id']}' aria='{data.get('aria','')}' testid='{data.get('testid','')}'>")
                    elif data['type'] == 'READY':
                        print(f"  [{t}] Listener listo en la pagina")
                except Exception:
                    pass

        page.on("console", handle_console)

        async def inject_on_load(frame):
            if frame == page.main_frame:
                try:
                    await page.evaluate(INJECT_JS)
                except Exception:
                    pass

        page.on("framenavigated", inject_on_load)

        await page.goto(META_BUSINESS_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        await page.evaluate(INJECT_JS)

        print("\n[OK] Browser abierto en Meta Business Suite.")
        print("     Cada accion que hagas aparece logueada en tiempo real.")
        print()
        input("Presiona Enter cuando termines el flujo completo de programar un Reel...")

        await context.close()

    print("\n" + "="*60)
    print("RESUMEN DE ACCIONES GRABADAS")
    print("="*60)
    for i, a in enumerate(actions):
        if a['type'] == 'CLICK':
            print(f"[{i+1}] CLICK   {a['selector']}")
            if a.get('aria'):    print(f"       aria-label:  '{a['aria']}'")
            if a.get('testid'):  print(f"       data-testid: '{a['testid']}'")
            if a.get('role'):    print(f"       role:        '{a['role']}'")
            if a.get('text'):    print(f"       text:        '{a['text']}'")
        elif a['type'] == 'INPUT':
            print(f"[{i+1}] INPUT   {a['selector']} = '{a.get('value','')}'")
            if a.get('placeholder'): print(f"       placeholder: '{a['placeholder']}'")
        elif a['type'] == 'CHANGE':
            print(f"[{i+1}] CHANGE  {a['selector']} = '{a.get('value','')}'")
        elif a['type'] == 'DIALOG_OPEN':
            print(f"[{i+1}] DIALOG  <{a['tag']} id='{a['id']}'  testid='{a.get('testid','')}'>")

    output_file = "debug_instagram_log.json"
    with open(output_file, "w") as f:
        json.dump(actions, f, indent=2, ensure_ascii=False)
    print(f"\nLog completo guardado en: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
