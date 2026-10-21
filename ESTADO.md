# Estado del proyecto — Shorts Uploader

> Última actualización: 2026-10-21

---

## Estado por plataforma

| Plataforma | Estado | Notas |
|---|---|---|
| YouTube | FUNCIONANDO | Browser (Playwright). Programado probado end-to-end el 2026-10-14. |
| TikTok | FUNCIONANDO | Browser (Playwright). Programado a otro dia probado el 2026-10-14. |
| Instagram | FUNCIONANDO | n8n en skynet + Cloudflare R2 (ver README). Publicacion real probada end-to-end el 2026-10-21. |

YouTube y TikTok corren en paralelo desde la app. La app solo marca OK cuando cada plataforma confirmo la programacion (subida al 100% + confirmacion de la plataforma); recien ahi se puede cerrar.

---|---|---|
| YouTube | FUNCIONANDO | Probado end-to-end. Se programa y publica correctamente. |
| TikTok | FUNCIONANDO* | Caption, upload y scheduling OK. Verificación final pendiente. |
| Instagram | INCOMPLETO | El bot ejecuta el flujo pero Meta no muestra el Reel en Scheduled. Ver sección de bugs. |

---

## YouTube

Flujo completo funcionando:
- Navega a YouTube Studio
- Sube el video vía file input (`[name="Filedata"]`)
- Escribe título y descripción
- Marca "No para niños"
- Abre configuración avanzada: idioma (Español) y categoría
- Agrega tags
- Navega Siguiente × 3
- Selecciona "Programado", ingresa fecha y hora
- Click "Programar"

**Timezone crítica:** El código convierte 17:00 ART a la timezone del browser. Por defecto asume `Europe/Rome`. Si la Mac está en otra zona horaria, actualizar `browser_tz` en `uploaders/youtube.py`.

---

## TikTok

Flujo completo funcionando:
- Navega a TikTok Creator Center
- Espera que cargue el input file (maneja redirect de login)
- Sube el video
- Remueve overlay `#react-joyride-portal`
- Escribe caption con Draft.js (limpia el contenido con JS range + Backspace)
- Activa el radio "Schedule" vía JS (no via click directo al elemento)
- Abre el datepicker, selecciona hora y día
- Clickea "Publicar"
- Maneja el modal de copyright (`TUXModal`) si aparece

**Pendiente:** Confirmar que el video aparece como "Programado" en TikTok y se publica a la hora correcta en el primer test real.

---

## Instagram

### Lo que hace el bot

El bot ejecuta el flujo completo sin errores Python:
1. Navega a Meta Business Suite (`business.facebook.com`)
2. Click "Create reel"
3. Sube el video vía file chooser
4. Escribe el caption en `div._5rpu[role="textbox"]`
5. Espera que Next se habilite (el video procesa, Meta reemplaza el elemento DOM)
6. Click Next (Create → Edit) vía JS evaluate
7. Click Next (Edit → Share) vía JS evaluate
8. Activa el toggle "Schedule"
9. Ingresa fecha vía `input[placeholder="mm/dd/yyyy"]` + calendario
10. Ingresa hora/minutos/AM-PM vía spinbuttons con `aria-label`
11. Clickea el botón Submit "Schedule" (lógica `hasDraftSibling`)

### El problema

Los Reels programados **no aparecen** en:
- La pestaña "Scheduled" de Meta Business Suite
- El Planner (vista calendario) de Meta Business Suite
- La sección "Programado" de la app mobile de Instagram

**Causa:** Bug conocido y crónico de Meta Business Suite. Sin ETA de fix. Múltiples usuarios reportan el mismo problema.

### Verificación pendiente

El test del 2026-05-08 programó un Reel para las 15:00 ART. Si aparece en el feed de Instagram a esa hora, el flujo funciona aunque el scheduler no lo muestre.

### Alternativas investigadas

| Alternativa | Viabilidad | Problema |
|---|---|---|
| instagram.com web | No disponible | No tiene scheduler nativo, solo publicación inmediata |
| App mobile | No automatizable | Requeriría Android emulado (Appium), mucho más complejo |
| Instagram Graph API | Viable | Puede quitar audio por copyright. Requiere access token de larga duración. |

**Si el Reel no se publica hoy:** evaluar migrar `uploaders/instagram.py` a la Graph API de Meta.

---

## Fixes técnicos aplicados

### playwright-stealth v2

```python
# API nueva (v2.x) — aplicada en los 3 uploaders
from playwright_stealth import Stealth
await Stealth().apply_stealth_async(page)
```

### Instagram: botón Next con element staleness

Meta reemplaza el elemento DOM del botón Next cuando lo habilita (no cambia un atributo — crea un elemento nuevo). Usar `.get_attribute()` en loop devuelve la referencia vieja.

Fix: `wait_for_function()` + `evaluate()` con búsqueda en el DOM fresco cada vez.

### Instagram: IDs dinámicos

Los IDs `js_*` de MBS se generan por sesión y cambian en cada carga. Reemplazados por selectores de atributos estables:
- `input[placeholder="mm/dd/yyyy"]` para la fecha
- `[role="spinbutton"][aria-label="hours/minutes/meridiem"]` para el tiempo

### Instagram: Schedule submit vs radio toggle

Dos elementos tienen texto "Schedule". El radio tiene `aria-pressed="true"` y tiene "Save as draft" como sibling en el DOM. El submit no. La lógica `hasDraftSibling` sube hasta 6 niveles en el árbol DOM buscando un sibling "Save as draft" para distinguirlos.

### TikTok: Draft.js caption clear

`Ctrl+A` + `Delete` no limpia el editor Draft.js. Fix: `document.createRange()` para seleccionar todo el contenido del nodo + `Backspace`.

### TikTok: selector de día en calendario

`span.day.valid` no matchea en TikTok. Fix: iterar todos los `span`, excluir los que tienen "timepicker" en su clase, clickear el que coincide con el día buscado.

### TikTok: modal de copyright

```python
modal = page.locator('.TUXModal')
if await modal.is_visible(timeout=4000):
    await page.locator('.TUXButton--primary').first.click(timeout=5000)
```

---

## Cómo debuggear

Los 3 uploaders tienen un DOM event logger inyectado vía `page.evaluate()`. Imprime en consola cada CLICK, INPUT y CHANGE con el tag, id, texto y aria-label del elemento. Prefijos: `[YTBOT]`, `[TTBOT]`, `[IGBOT]`.

Para correr un uploader aislado:

```bash
source venv/bin/activate
python test_instagram.py   # o test_tiktok.py, test_youtube.py
```

---

## Próximos pasos

- [ ] Instagram programado: servicio en skynet (systemd timer) con cola de videos. La app manda video + job por `scp` via Tailscale; a la hora, skynet sube a hosting temporal, crea el container y hace `media_publish`, despues borra el video. Pendiente hasta mover skynet a una conexion de red fija.
- [ ] Reemplazar las esperas fijas (`asyncio.sleep`) que quedan en los uploaders por esperas a elementos.
- [ ] Investigar cuelgue visto una vez en YouTube al cerrar el browser (hay logs en el paso 22).
