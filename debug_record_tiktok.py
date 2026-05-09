"""
Abre TikTok Creator Center y registra cada interaccion manual.
Uso: python debug_record_tiktok.py
Hace todo vos en el browser. Cuando termines presiona Enter en la terminal.
"""
import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import SESSIONS_DIR, TIKTOK_UPLOAD_URL

INJECT_JS = """
window.__log = [];

function getSelector(el) {
    if (!el || el === document.body) return 'body';
    if (el.id) return '#' + el.id;
    if (el.getAttribute('aria-label')) return `[aria-label="${el.getAttribute('aria-label')}"]`;
    if (el.getAttribute('name')) return `[name="${el.getAttribute('name')}"]`;
    if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
    if (el.getAttribute('data-e2e')) return `[data-e2e="${el.getAttribute('data-e2e')}"]`;
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
        e2e: el.getAttribute('data-e2e') || '',
        name: el.getAttribute('name') || '',
        placeholder: el.getAttribute('placeholder') || '',
        type: el.getAttribute('type') || '',
        classes: el.className?.toString().slice(0, 80) || '',
        text: el.innerText?.trim().slice(0, 60) || '',
    };
}

document.addEventListener('click', (e) => {
    const el = e.target;
    const closest = el.closest('button, [role=button], input, a, [role=tab], [role=menuitem], [role=option], div[tabindex], span[role=button]') || el;
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
                        e2e: node.getAttribute?.('data-e2e') || '',
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
    print("GRABADOR DE SESION — TikTok Creator Center")
    print("="*60)
    print("1. Se abre Chrome con tu sesion de TikTok")
    print("2. Hace el flujo completo a mano:")
    print("   - Click en 'Select video' o subir video")
    print("   - Esperar que cargue y procese")
    print("   - Escribir caption (titulo + descripcion + hashtags)")
    print("   - Configurar opciones (publico, permite comentarios, etc.)")
    print("   - Cambiar a 'Schedule' en vez de 'Post now'")
    print("   - Elegir fecha y hora")
    print("   - Click en 'Schedule' o 'Post'")
    print("3. Cuando termines presiona Enter en esta terminal")
    print("="*60)
    input("Presiona Enter para abrir el browser...")

    actions = []

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(SESSIONS_DIR / "tiktok"),
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
                        aria  = data.get('aria', '')
                        testid = data.get('testid', '')
                        e2e   = data.get('e2e', '')
                        role  = data.get('role', '')
                        txt   = data.get('text', '')
                        id_   = data.get('id', '')
                        print(f"  [{t}] CLICK   → {data['selector']}")
                        if aria:   print(f"           aria-label:  '{aria}'")
                        if testid: print(f"           data-testid: '{testid}'")
                        if e2e:    print(f"           data-e2e:    '{e2e}'")
                        if role:   print(f"           role:        '{role}'")
                        if txt:    print(f"           text:        '{txt}'")
                        if id_:    print(f"           id:          '{id_}'")
                    elif data['type'] == 'INPUT':
                        print(f"  [{t}] INPUT   → {data['selector']}  value: '{data.get('value', '')}'")
                        ph = data.get('placeholder', '')
                        if ph: print(f"           placeholder: '{ph}'")
                        e2e = data.get('e2e', '')
                        if e2e: print(f"           data-e2e: '{e2e}'")
                    elif data['type'] == 'CHANGE':
                        print(f"  [{t}] CHANGE  → {data['selector']}  value: '{data.get('value', '')}'")
                    elif data['type'] == 'DIALOG_OPEN':
                        print(f"  [{t}] DIALOG  → <{data['tag']} id='{data['id']}' e2e='{data.get('e2e','')}'>")
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

        await page.goto(TIKTOK_UPLOAD_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        await page.evaluate(INJECT_JS)

        print("\n[OK] Browser abierto en TikTok Creator Center.")
        print("     Cada accion que hagas aparece logueada en tiempo real.")
        print()
        input("Presiona Enter cuando termines el flujo completo de programar un video...")

        await context.close()

    print("\n" + "="*60)
    print("RESUMEN DE ACCIONES GRABADAS")
    print("="*60)
    for i, a in enumerate(actions):
        if a['type'] == 'CLICK':
            print(f"[{i+1}] CLICK   {a['selector']}")
            if a.get('aria'):    print(f"       aria-label:  '{a['aria']}'")
            if a.get('testid'):  print(f"       data-testid: '{a['testid']}'")
            if a.get('e2e'):     print(f"       data-e2e:    '{a['e2e']}'")
            if a.get('role'):    print(f"       role:        '{a['role']}'")
            if a.get('text'):    print(f"       text:        '{a['text']}'")
        elif a['type'] == 'INPUT':
            print(f"[{i+1}] INPUT   {a['selector']} = '{a.get('value','')}'")
            if a.get('placeholder'): print(f"       placeholder: '{a['placeholder']}'")
            if a.get('e2e'):         print(f"       data-e2e:    '{a['e2e']}'")
        elif a['type'] == 'CHANGE':
            print(f"[{i+1}] CHANGE  {a['selector']} = '{a.get('value','')}'")
        elif a['type'] == 'DIALOG_OPEN':
            print(f"[{i+1}] DIALOG  <{a['tag']} id='{a['id']}'  e2e='{a.get('e2e','')}'>")

    output_file = "debug_tiktok_log.json"
    with open(output_file, "w") as f:
        json.dump(actions, f, indent=2, ensure_ascii=False)
    print(f"\nLog completo guardado en: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
