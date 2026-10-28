import gradio as gr
import asyncio
import queue
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, date
from pathlib import Path
import pytz

from config import DEFAULT_PUBLISH_HOUR, DEFAULT_PUBLISH_MINUTE, YT_CATEGORIES, YT_DEFAULT_CATEGORY
from utils import get_pending_videos, build_caption, move_to_finalized, get_schedule_datetime, load_mode, save_mode
from presets import get_today_preset, preset_labels, preset_by_label, day_from_label, save_preset_override
from uploaders.youtube import upload as yt_upload
from uploaders.tiktok import upload as tt_upload
from uploaders.instagram import upload as ig_upload

ART_TZ = pytz.timezone("America/Argentina/Buenos_Aires")

DIAS_ES = {
    0: "Lunes", 1: "Martes", 2: "Miercoles", 3: "Jueves",
    4: "Viernes", 5: "Sabado", 6: "Domingo",
}

THEME = gr.themes.Base()

# Todos los controles miden CTRL (40px): inputs, refresh, tabs, chips y boton.
UI_CSS = """
body {
  --c-bg: #0c0d0f; --c-panel: #131518; --c-raise: #1a1d21; --c-line: #262a30; --c-line-2: #33383f;
  --c-text: #e8e6e1; --c-dim: #8a8f97; --c-accent: #ff6a1a; --c-accent-dim: rgba(255,106,26,.14);
  --ctrl: 40px;
  --body-background-fill: var(--c-bg); --background-fill-primary: var(--c-panel); --background-fill-secondary: var(--c-raise);
  --body-text-color: var(--c-text); --body-text-color-subdued: var(--c-dim); --block-label-text-color: var(--c-dim); --block-title-text-color: var(--c-dim);
  --block-background-fill: transparent; --block-border-color: transparent; --border-color-primary: var(--c-line);
  --input-background-fill: var(--c-raise); --input-background-fill-focus: var(--c-raise); --input-border-color: var(--c-line); --input-border-color-focus: var(--c-accent);
  --input-radius: 4px; --input-shadow: none; --input-shadow-focus: 0 0 0 3px var(--c-accent-dim);
  --color-accent: var(--c-accent); --color-accent-soft: var(--c-accent-dim); --border-color-accent: var(--c-accent);
  --neutral-50: var(--c-raise); --neutral-100: var(--c-raise); --neutral-200: var(--c-line); --neutral-700: var(--c-text);
  --button-secondary-background-fill: var(--c-raise); --button-secondary-background-fill-hover: #23272c; --button-secondary-text-color: var(--c-text); --button-secondary-border-color: var(--c-line);
  --font: 'Inter Tight', system-ui, sans-serif; --font-mono: 'JetBrains Mono', ui-monospace, monospace;
  background: var(--c-bg) !important; color: var(--c-text); color-scheme: dark;
}

/* ---- Layout: ancho fijo (no depende del contenido de la pestana) ---- */
body .gradio-container { width: 100% !important; max-width: 1200px !important; margin: 0 auto !important; padding: 20px 28px !important; background: var(--c-bg) !important; font-family: var(--font) !important; box-sizing: border-box; }
body .main.fillable { width: 100% !important; max-width: none !important; padding: 0 !important; }
body footer { display: none !important; }
body #main-row { gap: 16px; align-items: stretch !important; }
body #col-form, body #col-publish { flex-basis: 0 !important; box-sizing: border-box; background: var(--c-panel); border: 1px solid var(--c-line); border-radius: 8px; padding: 18px !important; gap: 12px; }

/* ---- Gradio chrome off ---- */
body .form { background: none !important; border: none !important; box-shadow: none !important; gap: 12px !important; overflow: visible !important; }
body .block { padding: 0 !important; background: transparent !important; border: none !important; box-shadow: none !important; }
body .block.hide-container { margin: 0 !important; min-height: 0 !important; }
body .html-container, body .html-container .prose { padding: 0 !important; margin: 0 !important; }

/* ---- Header ---- */
body #header-row { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; padding: 0 0 14px; margin-bottom: 16px; border-bottom: 1px solid var(--c-line); }
body #header-row h1 { display: flex; align-items: center; gap: 10px; margin: 0; font-family: var(--font); font-size: 1.15rem; font-weight: 600; letter-spacing: -0.01em; color: var(--c-text); }
body .brand-mark { width: 8px; height: 8px; border-radius: 50%; background: var(--c-accent); box-shadow: 0 0 0 3px var(--c-accent-dim), 0 0 12px rgba(255,106,26,.6); }
body #header-row p { margin: 0; font-family: var(--font-mono); font-size: .74rem; color: var(--c-dim); text-transform: uppercase; letter-spacing: .06em; }
body .hdr-topic { color: var(--c-text); }
body .hdr-sep { margin: 0 10px; color: var(--c-line-2); }

/* ---- Labels ---- */
body .block label.container > span:first-child,
body .block div.container > span:first-child,
body #platform-chips > span,
body .section-label {
  margin: 0 0 6px; font-family: var(--font-mono) !important; font-size: .68rem !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: .1em; color: var(--c-dim) !important;
}

/* ---- Inputs ---- */
body textarea, body .block .wrap:has(input[role=listbox]) { font-size: .9rem !important; color: var(--c-text) !important; border: 1px solid var(--c-line) !important; background: var(--c-raise) !important; border-radius: 4px !important; }
body .block .wrap:has(input[role=listbox]) { min-height: var(--ctrl); box-sizing: border-box; }
body textarea:focus, body .block .wrap:has(input:focus) { border-color: var(--c-accent) !important; box-shadow: 0 0 0 3px var(--c-accent-dim) !important; }
body input[role=listbox] { color: var(--c-text) !important; }
body ul.options { background: var(--c-raise) !important; border: 1px solid var(--c-line-2) !important; border-radius: 4px !important; }
body ul.options li.active, body ul.options li:hover { background: var(--c-accent-dim) !important; color: var(--c-text) !important; }

/* ---- Refresh ---- */
body #refresh-btn { align-self: flex-end; flex: 0 0 var(--ctrl) !important; min-width: var(--ctrl) !important; height: var(--ctrl); padding: 0 !important; background: var(--c-raise) !important; border: 1px solid var(--c-line) !important; border-radius: 4px !important; color: var(--c-dim) !important; font-size: 1rem; transition: transform 160ms cubic-bezier(0.23, 1, 0.32, 1), background-color 150ms ease-out, color 150ms ease-out; }
body #refresh-btn:hover { color: var(--c-text) !important; background: #23272c !important; }
body #refresh-btn:active { transform: scale(0.94); }

/* ---- Tabs de modo: mismo alto y estilo que los chips ---- */
body #mode-tabs .tab-container[role=tablist] { display: grid !important; grid-template-columns: 1fr 1fr; gap: 6px; height: auto; margin-top: 6px; padding: 0; background: none; border: none !important; }
body #mode-tabs .tab-container[role=tablist] button { height: var(--ctrl); padding: 0 10px !important; justify-content: center; border: 1px solid var(--c-line) !important; border-radius: 4px !important; background: var(--c-raise) !important; font-family: var(--font-mono); font-size: .74rem !important; text-transform: uppercase; letter-spacing: .06em; color: var(--c-dim) !important; transition: border-color 150ms ease-out, color 150ms ease-out, box-shadow 150ms ease-out; }
body #mode-tabs .tab-container[role=tablist] button::after { display: none !important; }
body #mode-tabs .tab-container[role=tablist] button:hover { color: var(--c-text) !important; border-color: var(--c-line-2) !important; }
body #mode-tabs .tab-container[role=tablist] button.selected { color: var(--c-text) !important; border-color: var(--c-line-2) !important; box-shadow: inset 0 -2px 0 var(--c-accent); }
/* Mismo alto en las dos pestanas: lo de abajo no salta al cambiar de modo */
body #mode-tabs .tabitem { min-height: 116px; box-sizing: border-box; padding: 12px 0 0 !important; border: none !important; background: none !important; }
body .mode-note, body .mode-note * { font-size: .82rem !important; color: var(--c-dim) !important; }

/* ---- Chips de plataformas ---- */
body #platform-chips input[type="checkbox"] { position: absolute; opacity: 0; pointer-events: none; }
body #platform-chips .wrap { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
body #platform-chips label { display: flex; align-items: center; gap: 8px; height: var(--ctrl); box-sizing: border-box; margin: 0; padding: 0 12px; cursor: pointer; user-select: none; border-radius: 4px; border: 1px solid var(--c-line); background: var(--c-raise) !important; color: var(--c-dim) !important; font-size: .82rem; font-weight: 500; transition: border-color 150ms ease-out, color 150ms ease-out; }
body #platform-chips label::before { content: ""; width: 7px; height: 7px; flex: none; border-radius: 50%; background: #3a3f46; transition: background-color 150ms ease-out, box-shadow 150ms ease-out; }
body #platform-chips label:hover { border-color: var(--c-line-2); color: var(--c-text) !important; }
body #platform-chips label:has(input:checked) { color: var(--c-text) !important; border-color: var(--c-line-2); }
body #platform-chips label:has(input:checked)::before { background: var(--c-accent); box-shadow: 0 0 8px rgba(255,106,26,.8); }
body #platform-chips label span { margin: 0 !important; }

/* ---- Boton publicar ---- */
body #publish-btn { width: 100%; height: var(--ctrl); min-height: var(--ctrl); padding: 0 !important; border: none !important; border-radius: 4px !important; background: var(--c-accent) !important; color: #140700 !important; font-family: var(--font-mono) !important; font-size: .78rem !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: .1em; transition: transform 160ms cubic-bezier(0.23, 1, 0.32, 1), background-color 150ms ease-out; }
body #publish-btn:hover { background: #ff7d36 !important; }
body #publish-btn:active { transform: scale(0.98); }

/* ---- Log: ocupa todo el alto que queda en la columna ---- */
body #col-publish > .form:last-child, body #log-area, body #log-area label.container, body #log-area .input-container { flex: 1 1 auto !important; display: flex; flex-direction: column; min-height: 0; }
body #log-area textarea { flex: 1 1 auto; height: 0 !important; min-height: 120px; max-height: none !important; resize: none; font-family: var(--font-mono) !important; font-size: .76rem !important; line-height: 1.6; background: #08090a !important; color: #b9e8a8 !important; border-color: var(--c-line) !important; }
"""

# Gradio rompe los @media que van en css= (les antepone un prefijo), por eso van en head.
HEAD = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
@media (max-width: 640px) {
  body .gradio-container { padding: 16px !important; }
  body #header-row p { line-height: 1.6; }
}
@media (prefers-reduced-motion: reduce) {
  body * { transition-duration: 0ms !important; }
}
</style>
"""


def get_video_choices() -> list[str]:
    return [v.name for v in get_pending_videos()]


def apply_preset(label: str) -> tuple[str, str]:
    preset = preset_by_label(label)
    return preset["hashtags"], preset["keywords"]


def on_tab_change(mode: str):
    save_mode(mode)


def run_upload(
    mode: str,
    video_name: str,
    title: str,
    description: str,
    hashtags: str,
    keywords_raw: str,
    preset_label: str,
    category_label: str,
    language: str,
    pub_date: str,
    pub_time: str,
    platforms: list[str],
):
    from config import PENDING_DIR

    if not platforms:
        yield "Error: selecciona al menos una plataforma."
        return

    if not video_name:
        yield "Error: selecciona un video."
        return

    video_path = PENDING_DIR / video_name
    if not video_path.exists():
        yield f"Error: no se encontro el video en {video_path}"
        return

    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    category_id = YT_CATEGORIES.get(category_label, YT_DEFAULT_CATEGORY)
    caption = build_caption(title, description, hashtags)

    now = datetime.now(ART_TZ)

    if mode == "publicar":
        # None = publicar ya en YouTube y TikTok; n8n publica Instagram apenas
        # termina de preparar el container (~2-5 min)
        ig_dt = now
        yt_dt = None
        tt_dt = None
    else:
        ig_dt = get_schedule_datetime(pub_date, pub_time)
        yt_dt = get_schedule_datetime(pub_date, pub_time)
        tt_dt = get_schedule_datetime(pub_date, pub_time)
        # TikTok rechaza horarios a menos de ~15 min; validar antes de abrir browsers
        if {"YouTube", "TikTok"} & set(platforms) and yt_dt - now < timedelta(minutes=20):
            yield "Error: la fecha/hora tiene que ser al menos 20 minutos en el futuro."
            return
        if ig_dt < now:
            yield "Error: la fecha/hora ya paso."
            return

    results = {"youtube": None, "tiktok": None, "instagram": None}
    errors = {}
    log = ""

    def emit(msg: str) -> str:
        nonlocal log
        log += msg
        return log

    plataformas_str = " + ".join(platforms)
    if mode == "publicar":
        yield emit(f"Modo: PUBLICAR — {plataformas_str}\n")
    else:
        yield emit(f"Modo: PROGRAMAR — {pub_time} ART del {pub_date} — {plataformas_str}\n")
    yield emit(f"Video: {video_name}\n")
    yield emit("---\n")

    # Las tres corren en paralelo. Cada una avisa por la cola apenas la plataforma
    # confirmo, sin esperar a que cierre el browser (el cierre de TikTok a veces
    # se cuelga y antes eso dejaba sin aviso a TikTok y sin correr a Instagram).
    events = queue.Queue()
    loops = {}

    async def tracked(key, coro):
        loops[key] = asyncio.get_running_loop()
        return await coro

    def run_job(key, make_coro):
        try:
            result = asyncio.run(tracked(key, make_coro(lambda: events.put((key, "ok", "")))))
            events.put((key, "ok", result if key == "instagram" else ""))
        except Exception as e:
            events.put((key, "error", str(e)))

    jobs = {}
    if "YouTube" in platforms:
        jobs["youtube"] = lambda done: yt_upload(
            str(video_path), title, description, hashtags,
            keywords, language, category_id, yt_dt, on_confirmed=done,
        )
    if "TikTok" in platforms:
        jobs["tiktok"] = lambda done: tt_upload(
            str(video_path), title, description, hashtags, tt_dt, on_confirmed=done,
        )
    if "Instagram" in platforms:
        jobs["instagram"] = lambda done: ig_upload(str(video_path), caption, ig_dt)
    names = {"youtube": "YouTube", "tiktok": "TikTok", "instagram": "Instagram"}
    for key in ("youtube", "tiktok", "instagram"):
        if key not in jobs:
            results[key] = "skipped"
            yield emit(f"{names[key]}: SKIPPED\n")

    if jobs:
        yield emit(" + ".join(names[k] for k in jobs) + ": subiendo en paralelo...\n")
        pool = ThreadPoolExecutor(max_workers=len(jobs))
        futures = {key: pool.submit(run_job, key, make_coro) for key, make_coro in jobs.items()}

        pending = set(jobs)
        deadline = time.monotonic() + 35 * 60
        while pending:
            try:
                key, status, detail = events.get(timeout=max(1, deadline - time.monotonic()))
            except queue.Empty:
                break
            if key not in pending:
                continue  # ya habia avisado al confirmar
            pending.discard(key)
            results[key] = status
            if status == "ok":
                yield emit(f"{names[key]}: OK{f' — {detail}' if detail else ''}\n")
            else:
                errors[key] = detail
                yield emit(f"{names[key]}: ERROR — {detail}\n")
        for key in pending:
            results[key] = "error"
            errors[key] = "no respondio en 35 min"
            yield emit(f"{names[key]}: ERROR — no respondio en 35 min, revisar a mano\n")
        # no esperar a los browsers que no cerraron; si a los 60 s alguno sigue,
        # dejar en el log en que await quedo trabado
        pool.shutdown(wait=False)
        threading.Timer(60, dump_stuck, args=(futures, loops, names)).start()

        yield emit("---\n" + "\n".join(
            f"{names[k]}: {'OK' if results[k] == 'ok' else 'ERROR'}" for k in jobs
        ) + "\n")

    # Auto-guardar hashtags/keywords si el usuario los modifico
    day = day_from_label(preset_label)
    save_preset_override(day, hashtags, keywords_raw)

    # move_to_finalized solo si YouTube y TikTok estaban seleccionados y todo lo seleccionado salio OK
    both_selected = {"YouTube", "TikTok"} <= set(platforms)
    all_ok = all(v in ("ok", "skipped") for v in results.values())

    if both_selected and all_ok:
        metadata = {
            "video": video_name,
            "title": title,
            "description": description,
            "hashtags": hashtags,
            "keywords": keywords,
            "category_id": category_id,
            "language": language,
            "mode": mode,
            "platforms": platforms,
            "scheduled_for": (yt_dt or now).isoformat(),
            "uploaded_at": now.isoformat(),
            "results": results,
        }
        move_to_finalized(video_path, metadata)
        yield emit("\nFinalizado: video movido a ~/shorts-uploader/finalized/\n")
    elif not both_selected:
        yield emit("\nVideo NO movido a finalized (YouTube y TikTok no estaban ambos seleccionados).\n")
    else:
        yield emit("\nHubo errores. El video NO fue movido a finalized.\n")
        for platform, err in errors.items():
            if err:
                yield emit(f"  {platform}: {err}\n")


def dump_stuck(futures, loops, names):
    for key, fut in futures.items():
        loop = loops.get(key)
        if fut.done() or loop is None:
            continue
        print(f"\n[DEBUG] {names[key]} sigue sin terminar 60 s despues. Donde quedo esperando:", flush=True)
        for task in asyncio.all_tasks(loop):
            coro = task.get_coro()
            while coro is not None:  # bajar por la cadena de awaits hasta el ultimo
                frame = getattr(coro, "cr_frame", None) or getattr(coro, "gi_frame", None)
                if frame:
                    print(f"  {frame.f_code.co_filename}:{frame.f_lineno} en {frame.f_code.co_name}")
                coro = getattr(coro, "cr_await", None) or getattr(coro, "gi_yieldfrom", None)
        # sospecha: GoogleUpdater (lo lanza Chrome al cerrar) retiene el stderr y Playwright no termina
        updater = subprocess.run(["pgrep", "-fl", "GoogleUpdater"], capture_output=True, text=True).stdout.strip()
        print(f"[DEBUG] GoogleUpdater corriendo: {updater or 'no'}")
        sys.stdout.flush()


def build_ui():
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    default_time = f"{DEFAULT_PUBLISH_HOUR:02d}:{DEFAULT_PUBLISH_MINUTE:02d}"
    day_name, today_preset = get_today_preset()
    dia_es = DIAS_ES[today.weekday()]
    saved_mode = load_mode()

    CHIPS_PUBLICAR  = ["YouTube", "TikTok", "Instagram"]
    CHIPS_PROGRAMAR = ["YouTube", "TikTok", "Instagram"]

    with gr.Blocks(title="Shorts Uploader") as app:

        gr.HTML(f"""
        <div id="header-row">
            <h1><span class="brand-mark" aria-hidden="true"></span>Shorts Uploader</h1>
            <p><span class="hdr-day">{dia_es} {today_str}</span><span class="hdr-sep">|</span><span class="hdr-topic">{today_preset['label'].split('—')[1].strip()}</span></p>
        </div>
        """)

        mode_state = gr.State(saved_mode)

        with gr.Row(equal_height=False, elem_id="main-row"):

            # ---- Columna izquierda: form fields ----
            with gr.Column(scale=3, min_width=300, elem_id="col-form"):

                with gr.Row(elem_id="video-row"):
                    video_dropdown = gr.Dropdown(
                        choices=get_video_choices(),
                        label="Video",
                        interactive=True,
                        scale=5,
                    )
                    refresh_btn = gr.Button("↻", size="sm", scale=1, min_width=40, elem_id="refresh-btn")

                title_input = gr.Textbox(label="Titulo", placeholder="Titulo del video")
                desc_input = gr.Textbox(
                    label="Descripcion", lines=3, placeholder="Descripcion completa"
                )

                preset_dropdown = gr.Dropdown(
                    choices=preset_labels(),
                    value=today_preset["label"],
                    label="Preset del dia",
                    interactive=True,
                )
                hashtags_input = gr.Textbox(
                    label="Hashtags (se replica a IG y TikTok)",
                    value=today_preset["hashtags"],
                    interactive=True,
                )
                keywords_input = gr.Textbox(
                    label="Keywords YouTube (separadas por coma)",
                    value=today_preset["keywords"],
                    interactive=True,
                )

                with gr.Row():
                    category_input = gr.Dropdown(
                        choices=list(YT_CATEGORIES.keys()),
                        value="Education (27)",
                        label="Categoria",
                        scale=3,
                    )
                    language_input = gr.Dropdown(
                        choices=["es", "en", "it"],
                        value="es",
                        label="Idioma",
                        scale=1,
                        min_width=80,
                    )

            # ---- Columna derecha: publicacion ----
            with gr.Column(scale=2, min_width=200, elem_id="col-publish"):

                gr.HTML('<p class="section-label">Modo de publicacion</p>')
                with gr.Tabs(selected=saved_mode, elem_id="mode-tabs") as tabs:
                    with gr.TabItem("Publicar ahora", id="publicar") as tab_publicar:
                        gr.Markdown(
                            "<small>Publica ya en las tres. Instagram tarda unos minutos (lo publica n8n en skynet).</small>",
                            elem_classes="mode-note",
                        )
                    with gr.TabItem("Programar", id="programar") as tab_programar:
                        with gr.Row():
                            date_input = gr.Textbox(
                                label="Fecha", value=today_str, scale=3, min_width=100
                            )
                            time_input = gr.Dropdown(
                                choices=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)],
                                value=default_time,
                                label="Hora ART",
                                scale=2,
                                min_width=90,
                            )
                        gr.Markdown("<small>Instagram lo programa n8n en skynet.</small>", elem_classes="mode-note")

                initial_chips = CHIPS_PUBLICAR if saved_mode == "publicar" else CHIPS_PROGRAMAR
                platform_chips = gr.CheckboxGroup(
                    choices=initial_chips,
                    value=initial_chips,
                    label="Plataformas",
                    elem_id="platform-chips",
                )

                run_btn = gr.Button("Publicar ahora", variant="primary", elem_id="publish-btn")

                log_output = gr.Textbox(
                    label="Log",
                    lines=10,
                    max_lines=10,
                    interactive=False,
                    elem_id="log-area",
                )

        # ---- Events ----
        def on_select_publicar():
            save_mode("publicar")
            return "publicar", gr.update(choices=CHIPS_PUBLICAR, value=CHIPS_PUBLICAR)

        def on_select_programar():
            save_mode("programar")
            return "programar", gr.update(choices=CHIPS_PROGRAMAR, value=CHIPS_PROGRAMAR)

        tab_publicar.select(fn=on_select_publicar, outputs=[mode_state, platform_chips])
        tab_programar.select(fn=on_select_programar, outputs=[mode_state, platform_chips])

        preset_dropdown.change(
            fn=apply_preset,
            inputs=[preset_dropdown],
            outputs=[hashtags_input, keywords_input],
        )

        refresh_btn.click(
            fn=lambda: gr.update(choices=get_video_choices()),
            outputs=video_dropdown,
        )

        run_btn.click(
            fn=run_upload,
            inputs=[
                mode_state,
                video_dropdown, title_input, desc_input, hashtags_input,
                keywords_input, preset_dropdown, category_input, language_input,
                date_input, time_input, platform_chips,
            ],
            outputs=log_output,
        )

    return app


if __name__ == "__main__":
    app = build_ui()
    app.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True, theme=THEME, css=UI_CSS, head=HEAD)
