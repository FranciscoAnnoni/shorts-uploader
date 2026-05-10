# Plan: Modo Publicar / Programar en Shorts Uploader

**Objetivo:** Agregar dos modos de publicación en la UI — "Publicar" (sube lo antes posible en cada plataforma) y "Programar" (scheduling con fecha/hora), con la elección persistida entre sesiones.

**Alcance:**
- Incluye: cambios en UI (main.py), lógica de modo en run_upload, cambios en youtube.py para publicación inmediata, ajuste de tiempos en tiktok.py, archivo de config de modo, test de publicación inmediata
- No incluye: scheduling de Instagram (bloqueado por Meta, se skipea en modo Programar sin romper el flujo)

**Criterio de éxito:** Correr main.py, elegir "Publicar", subir el video de test, e Instagram publica ahora, YouTube en ~10 min, TikTok en ~25 min. Reiniciar el servidor y que el modo quede guardado.

---

## Fase 1: Test de publicación inmediata en Instagram
**Objetivo:** Confirmar que el token actual publica inmediatamente antes de tocar nada más.
**Entregable:** Reel publicado en @frannoni_ con el video de test.

**Pasos:**
- [ ] Correr test con el token actual e IG_USER_ID=17841475738858818
- [ ] Confirmar que aparece en Instagram
- [ ] Francisco lo borra manualmente

---

## Fase 2: Archivo de config de modo
**Objetivo:** Persistir la elección publicar/programar entre reinicios del servidor.
**Entregable:** `uploader-mode.json` en la raíz del repo.

**Pasos:**
- [ ] Crear `uploader-mode.json` con valor default `{"mode": "publicar"}`
- [ ] Agregar a `.gitignore` para que no genere ruido en git
- [ ] Agregar helpers `load_mode()` / `save_mode(mode)` en utils.py

---

## Fase 3: Cambios en UI (main.py)
**Objetivo:** Reemplazar sección "Programar publicación" por dos tabs.
**Entregable:** UI con tabs "Publicar" / "Programar publicación", modo guardado al cambiar de tab.

**Pasos:**
- [ ] Reemplazar la sección de fecha/hora con `gr.Tabs`
- [ ] Tab "Publicar": texto "El contenido será publicado en este momento (Instagram ahora, YouTube en ~10 min, TikTok en ~25 min)"
- [ ] Tab "Programar publicación": fecha + hora inputs idénticos a los actuales
- [ ] Al iniciar el servidor: pre-seleccionar el tab según `uploader-mode.json`
- [ ] Al cambiar de tab: guardar el nuevo modo en `uploader-mode.json` automáticamente
- [ ] Botón siempre dice "PUBLICAR EN LAS 3 PLATAFORMAS"

---

## Fase 4: Lógica de backend en run_upload (main.py)
**Objetivo:** Que run_upload use tiempos distintos según el modo y skipee Instagram en modo Programar.
**Entregable:** run_upload con rama `publicar` y rama `programar`.

**Pasos:**
- [ ] Agregar parámetro `mode` a `run_upload`
- [ ] Rama "publicar": construir schedule_dt por plataforma:
  - Instagram: `datetime.now(ART_TZ)` (inmediato)
  - YouTube: `datetime.now(ART_TZ) + 10 min`
  - TikTok: `datetime.now(ART_TZ) + 25 min`
- [ ] Rama "programar": usar fecha/hora del form (igual que hoy)
  - Instagram: skipear — emitir `"Instagram: SKIPPED (scheduling no disponible)\n"` en el log
  - YouTube y TikTok: flujo existente sin cambios
- [ ] Lógica de finalized/: mover si YouTube + TikTok OK (Instagram no cuenta para la decisión)

---

## Fase 5: YouTube — publicación inmediata
**Objetivo:** Que youtube.py soporte publicar en ~10 min (como "Programado" a futuro cercano).
**Entregable:** youtube.py acepta schedule_dt a 10 min en el futuro sin cambios de flujo.

**Pasos:**
- [ ] Verificar si YouTube Studio acepta un schedule a 10 min en el futuro
- [ ] Si acepta: no hay cambio en youtube.py, solo cambia el schedule_dt que le pasa main.py
- [ ] Si no acepta (mínimo mayor): ajustar el offset a lo mínimo que acepte

---

## Fase 6: TikTok — publicación en ~25 min
**Objetivo:** Que tiktok.py no rompa cuando recibe un schedule_dt a 25 min en el futuro.
**Entregable:** tiktok.py acepta el offset sin tirar ValueError.

**Pasos:**
- [ ] Verificar que la validación `< 20 min` no rechace `now + 25 min` (no debería, pero confirmar)
- [ ] No hay cambios en la lógica del uploader — solo cambia el schedule_dt que recibe

---

## Fase 7: Test end-to-end
**Objetivo:** Verificar el flujo completo de ambos modos.
**Entregable:** Test pasado, video de test borrado por Francisco.

**Pasos:**
- [ ] Test modo "Publicar": correr main.py, subir test.mp4, confirmar publicación en las 3 plataformas
- [ ] Reiniciar servidor, confirmar que el modo "Publicar" se mantiene
- [ ] Test modo "Programar": cambiar a tab "Programar", programar a +2hs, confirmar que IG se skipea y YT/TT quedan programados
- [ ] Reiniciar servidor, confirmar que el modo "Programar" se mantiene

---

## Decisiones tomadas
- Config de modo dentro del repo (`uploader-mode.json`) pero en `.gitignore` — simple y sin ruido en git
- Tab cambia = guarda automáticamente, sin botón de confirmación
- Tiempos en modo "Publicar": Instagram NOW, YouTube +10min, TikTok +25min (mínimo de plataforma)
- Instagram en modo "Programar": skipear silenciosamente, no romper el flujo ni impedir mover a finalized/
- finalized/ se mueve si YouTube + TikTok OK, independientemente de Instagram

## Riesgos y mitigaciones
- YouTube rechaza schedule a 10 min: ajustar a 15 min, verificar en Fase 5
- TikTok con +25 min coincide con otro video ya programado: es responsabilidad del usuario, no se valida
- Token de Instagram expira (60 días): pendiente implementar auto-refresh, fuera del alcance de este plan
