# Contexto: Shorts Uploader — Redesign UI v2

**Última actualización:** 2026-06-01
**Estado general:** completado

---

## Estado final de la UI

| Aspecto | Detalle |
|---------|---------|
| Fuente | Plus Jakarta Sans (Google Fonts, importada via CSS) |
| Color primario | #FF711F (naranja, solo en chips, botón, tab activo, focus) |
| Tema Gradio | `gr.themes.Soft(primary_hue=slate)` — labels en gris neutro |
| Layout | 2 columnas: izq (scale=3) formulario, der (scale=2) publicacion |
| Fondo | #f8f9fb |

---

## Columna izquierda

- Video dropdown + botón refresh (sin section label)
- Titulo (Textbox)
- Descripcion (Textbox, lines=3)
- Preset del dia (Dropdown)
- Hashtags (Textbox)
- Keywords YouTube (Textbox)
- Categoria + Idioma YouTube (Row con 2 Dropdowns)

Sin ningún `gr.HTML` de section label — se eliminaron porque ocupaban altura innecesaria.

## Columna derecha

- "MODO DE PUBLICACION" section label (se mantiene)
- Tabs `gr.Tabs(selected=saved_mode)`:
  - "Publicar ahora" → nota de tiempos
  - "Programar" → Fecha + Hora ART + nota Instagram
- `platform_chips` CheckboxGroup:
  - Publicar ahora: choices = ["YouTube", "TikTok", "Instagram"], value = todos
  - Programar: choices = ["YouTube", "TikTok"], value = ambos
  - Se actualiza dinámicamente al cambiar de tab
- Botón "Publicar ahora" (naranja, full width)
- Log (fondo negro, monospace)

---

## CSS clave

- `@import` Plus Jakarta Sans
- `* { font-family: Plus Jakarta Sans !important }`
- `.block.hide-container { padding: 0 !important; margin: 6px 0 0 0 !important; }` — elimina el padding extra de los gr.HTML blocks
- `#platform-chips label:has(input:checked) { background: #FF711F }` — chips naranjas al estar activos
- `#publish-btn { background: #FF711F !important }` — botón naranja
- `body, .gradio-container { background: #f8f9fb }` — fondo claro

## Lógica de plataformas

- `run_upload` recibe `platforms: list[str]`
- YouTube: `if "YouTube" in platforms`
- TikTok: `if "TikTok" in platforms`
- Instagram: `if mode == "publicar" and "Instagram" in platforms`
- `move_to_finalized` solo si YouTube + TikTok ambos OK y ambos seleccionados

## Para retomar

Abrir `main.py` y hacer cambios directamente. La app corre con:
```
cd ~/Proyectos/shorts-uploader && source venv/bin/activate && python main.py
```
