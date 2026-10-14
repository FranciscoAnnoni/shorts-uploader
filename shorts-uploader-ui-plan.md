# Plan: Shorts Uploader — Platform Chips + UI Redesign

**Objetivo:** Agregar selección de plataforma (YouTube / TikTok como toggles independientes) y rediseñar la UI con tema violeta en layout de dos columnas que entre en 1920x1080.

**Alcance:**
- Incluye: chips de plataforma, lógica de upload condicional, tema violeta, layout 2 columnas, botón siempre dice "PUBLICAR"
- No incluye: cambios en los uploaders individuales, nuevas plataformas, lógica de Instagram (sigue igual)

**Criterio de éxito:** La app corre en `python main.py`, se ve en 1920x1080 sin scroll vertical, los chips de plataforma funcionan, y la lógica de upload respeta la selección.

---

## Fase 1: Lógica de platform selection en `run_upload`

**Objetivo:** Que `run_upload` reciba qué plataformas están activas y salte las que no.

**Entregable:** `main.py` — función `run_upload` actualizada.

**Pasos:**
- [ ] Agregar parámetro `platforms: list[str]` a `run_upload` (valores posibles: `["YouTube"]`, `["TikTok"]`, `["YouTube", "TikTok"]`)
- [ ] Validar al inicio: si `platforms` está vacío, yield error y return (no debería pasar pero es defensa)
- [ ] Bloque YouTube: wrapearlo en `if "YouTube" in platforms`
- [ ] Bloque TikTok: wrapearlo en `if "TikTok" in platforms`
- [ ] Bloque Instagram: sin cambios (sigue dependiendo del modo publicar/programar)
- [ ] Lógica `move_to_finalized`: cambiar condición. Actualmente: `yt_ok and tt_ok`. Nueva lógica:
  - Si platforms == ["YouTube", "TikTok"]: mover solo si ambos OK (igual que antes)
  - Si platforms == ["YouTube"] o ["TikTok"]: NO mover a finalized (comportamiento solicitado explícitamente)
  - Emitir en el log: "Video NO movido a finalized (solo se subió a una plataforma)"
- [ ] Agregar `"platforms": platforms` al dict `metadata` que se guarda en el JSON de finalized

---

## Fase 2: UI — Layout 2 columnas + tema violeta

**Objetivo:** Rediseñar `build_ui()` con un layout moderno tipo upload-form que entre en 1920x1080 sin scroll.

**Entregable:** `build_ui()` reescrita en `main.py`.

**Decisiones de layout:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  Shorts Uploader                          Hoy: Lunes 2026-06-01     │
├──────────────────────────┬──────────────────────────────────────────┤
│   COLUMNA IZQUIERDA      │   COLUMNA DERECHA                        │
│   (video + publicar)     │   (contenido + configuración)            │
│                          │                                          │
│  [ Video dropdown    ↻ ] │  Titulo: [__________________________]   │
│                          │                                          │
│  MODO                    │  Descripcion: [____________________]    │
│  ┌──────────┬──────────┐ │               [____________________]    │
│  │ Publicar │ Programar│ │               [____________________]    │
│  └──────────┴──────────┘ │                                          │
│  (si Programar: fecha/h) │  Preset: [Lunes — Humor ▾          ]    │
│                          │  Hashtags: [_______________________]    │
│  PLATAFORMAS             │  Keywords: [_______________________]    │
│  [▣ YouTube] [▣ TikTok] │                                          │
│                          │  YouTube                                 │
│  [ PUBLICAR ▶ ]          │  Categoria: [Education ▾] Idioma: [es▾] │
│                          │                                          │
│  ┌────────────────────┐  │                                          │
│  │ Log de ejecución   │  │                                          │
│  │                    │  │                                          │
│  └────────────────────┘  │                                          │
└──────────────────────────┴──────────────────────────────────────────┘
```

**Pasos:**
- [ ] Aplicar tema violeta: `gr.themes.Soft(primary_hue=gr.themes.colors.violet, secondary_hue=gr.themes.colors.purple, neutral_hue=gr.themes.colors.slate)`
- [ ] Agregar CSS custom para chips (ver abajo)
- [ ] Reestructurar `build_ui()` con `gr.Row()` de 2 columnas usando `scale=`
  - Columna izquierda `scale=2`: video dropdown + refresh, tabs publicar/programar, platform chips, botón PUBLICAR, log output
  - Columna derecha `scale=3`: título, descripción, preset dropdown, hashtags, keywords, categoria, idioma
- [ ] Header: una sola línea con título + fecha del día en la misma fila
- [ ] Platform chips: `gr.CheckboxGroup(choices=["YouTube", "TikTok"], value=["YouTube", "TikTok"], elem_id="platform-chips", label="Publicar en")`
- [ ] CSS para chips: transformar los checkboxes de `#platform-chips` en chips pill-shaped con fondo violeta cuando están activos
- [ ] Log output: reducir height a 10 líneas (en 1080p alcanza)
- [ ] Descripción: reducir a 3 líneas (lines=3)
- [ ] Conectar `platform_chips` al `run_upload`: agregar como input en `run_btn.click()`

---

## Fase 3: CSS de chips

**Objetivo:** Que los 2 checkboxes de plataforma parezcan chips modernos, no checkboxes de formulario.

**CSS a inyectar vía `gr.HTML` o `gr.Blocks(css=...)`:**

```css
/* Platform chips */
#platform-chips .wrap {
    display: flex;
    gap: 8px;
    flex-wrap: nowrap;
}
#platform-chips label {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    border-radius: 999px;
    border: 2px solid #7c3aed;
    background: transparent;
    color: #7c3aed;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    user-select: none;
}
#platform-chips input[type="checkbox"]:checked + span,
#platform-chips label:has(input:checked) {
    background: #7c3aed;
    color: white;
}
/* Ocultar el checkbox nativo */
#platform-chips input[type="checkbox"] {
    display: none;
}
```

**Pasos:**
- [ ] Pasar el CSS como string a `gr.Blocks(css=CSS_STRING, theme=...)`
- [ ] Verificar que los chips se ven correctamente con ambos seleccionados por default
- [ ] Verificar que al deseleccionar uno, el chip cambia de estado visual

---

## Fase 4: Validación y test

**Objetivo:** Confirmar que todo funciona antes de declarar terminado.

**Pasos:**
- [ ] `python main.py` — app levanta sin error
- [ ] Verificar que la UI entra en pantalla sin scroll (testearlo en 1920x1080 o similar)
- [ ] Seleccionar solo YouTube → click PUBLICAR → log muestra "TikTok: SKIPPED", video NO se mueve a finalized
- [ ] Seleccionar solo TikTok → click PUBLICAR → log muestra "YouTube: SKIPPED", video NO se mueve a finalized
- [ ] Seleccionar ambos → comportamiento igual que antes
- [ ] Deseleccionar ambos → error antes de ejecutar: "Seleccioná al menos una plataforma"
- [ ] Verificar que chips se ven violetas en el browser

---

## Decisiones tomadas

- **CheckboxGroup sobre Radio:** Permite togglear cada plataforma independientemente. Radio solo permitiría una opción predefinida ("YouTube", "TikTok", "Ambas") — menos flexible si en el futuro se agrega Instagram.
- **move_to_finalized solo con ambas:** Decisión explícita del usuario. Si se sube a una sola plataforma, el video queda en `pending/` para poder reintentarlo en la otra.
- **Botón siempre dice "PUBLICAR":** El feedback visual del resultado va al log. No se necesita texto dinámico en el botón.
- **Log en columna izquierda:** Queda visible junto al botón de acción, no al lado del contenido. Flujo más natural.

## Riesgos y mitigaciones

- **CSS de chips no funciona en versiones viejas de Gradio:** Usar `:has()` puede no estar disponible. Mitigación: en el CSS, agregar también la regla con `input:checked ~ span` como fallback.
- **Layout se rompe en pantallas más pequeñas:** El `scale=` de Gradio es relativo. Mitigación: testear al final y ajustar si hace falta con `min_width`.
- **CheckboxGroup value vacío al deseleccionar todo:** Gradio lo permite. Agregar validación al inicio de `run_upload` para bloquearlo antes de ejecutar.
