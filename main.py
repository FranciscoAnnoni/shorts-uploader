import gradio as gr
import asyncio
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

THEME = gr.themes.Soft(
    primary_hue=gr.themes.colors.slate,
    secondary_hue=gr.themes.colors.gray,
    neutral_hue=gr.themes.colors.slate,
)

CHIP_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

/* ---- Global font ---- */
*, *::before, *::after {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* ---- App background ---- */
body, .gradio-container {
    background: #f8f9fb !important;
}

/* ---- Header row ---- */
#header-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding-bottom: 10px;
    border-bottom: 1px solid #e0e4e8;
    margin-bottom: 10px;
}
#header-row h1 {
    margin: 0;
    font-size: 1.4rem;
    font-weight: 700;
    color: #191c1e;
    letter-spacing: -0.02em;
}
#header-row p {
    margin: 0;
    font-size: 0.82rem;
    color: #6c757d;
}

/* ---- Section labels ---- */
.section-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6c757d;
    margin: 0;
    padding: 0;
    line-height: 1.2;
}

/* ---- Section label containers (gr.HTML blocks) - kill excess padding ---- */
.block.hide-container {
    padding: 0 !important;
    margin: 6px 0 0 0 !important;
    min-height: 0 !important;
}

/* ---- Platform chips ---- */
#platform-chips .wrap {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    padding-top: 4px;
}
#platform-chips label.svelte-1ipelgc,
#platform-chips label {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 7px 20px;
    border-radius: 999px;
    border: 2px solid #FF711F;
    background: transparent;
    color: #FF711F;
    font-weight: 600;
    font-size: 0.9rem;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    user-select: none;
    margin: 0;
}
#platform-chips label:has(input:checked) {
    background: #FF711F;
    color: #ffffff;
}
#platform-chips input[type="checkbox"] {
    display: none;
}
#platform-chips .label-wrap,
#platform-chips > .form {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
    box-shadow: none !important;
    gap: 0 !important;
}

/* ---- Publish button ---- */
#publish-btn {
    background: #FF711F !important;
    border: none !important;
    border-radius: 0.5rem !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    color: #ffffff !important;
    width: 100% !important;
    padding: 14px !important;
    transition: background 0.15s !important;
    margin-top: 12px !important;
}
#publish-btn:hover {
    background: #e05e10 !important;
}

/* ---- Compact tabs ---- */
.tab-nav button { padding: 6px 18px !important; font-size: 0.85rem !important; }

/* ---- Log area ---- */
#log-area textarea {
    font-family: monospace !important;
    font-size: 0.8rem;
    background: #191c1e !important;
    color: #e0e3e5 !important;
    border-radius: 0.5rem !important;
}

/* ---- Input focus orange ---- */
input:focus, textarea:focus, select:focus {
    border-color: #FF711F !important;
    box-shadow: 0 0 0 2px rgba(255,113,31,0.15) !important;
}

/* ---- Tab active state orange ---- */
.tab-nav button.selected {
    color: #FF711F !important;
    border-color: #FF711F !important;
}

/* ---- Input labels - neutral gray ---- */
label > span:first-child {
    color: #6c757d !important;
    font-weight: 500 !important;
    font-size: 0.8rem !important;
}
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
        yield "Error: selecciona al menos una plataforma (YouTube o TikTok)."
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
        ig_dt = now
        yt_dt = now + timedelta(minutes=15)
        tt_dt = now + timedelta(minutes=30)
    else:
        ig_dt = get_schedule_datetime(pub_date, pub_time)
        yt_dt = get_schedule_datetime(pub_date, pub_time)
        tt_dt = get_schedule_datetime(pub_date, pub_time)

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

    if "YouTube" in platforms:
        yield emit("YouTube: subiendo...\n")
        try:
            asyncio.run(yt_upload(
                str(video_path), title, description, hashtags,
                keywords, language, category_id, yt_dt
            ))
            results["youtube"] = "ok"
            yield emit("YouTube: OK\n")
        except Exception as e:
            results["youtube"] = "error"
            errors["youtube"] = str(e)
            yield emit(f"YouTube: ERROR — {e}\n")
    else:
        results["youtube"] = "skipped"
        yield emit("YouTube: SKIPPED\n")

    if "TikTok" in platforms:
        yield emit("TikTok: subiendo...\n")
        try:
            asyncio.run(tt_upload(str(video_path), title, description, hashtags, tt_dt))
            results["tiktok"] = "ok"
            yield emit("TikTok: OK\n")
        except Exception as e:
            results["tiktok"] = "error"
            errors["tiktok"] = str(e)
            yield emit(f"TikTok: ERROR — {e}\n")
    else:
        results["tiktok"] = "skipped"
        yield emit("TikTok: SKIPPED\n")

    if mode == "publicar" and "Instagram" in platforms:
        yield emit("Instagram: subiendo...\n")
        try:
            asyncio.run(ig_upload(str(video_path), caption, ig_dt))
            results["instagram"] = "ok"
            yield emit("Instagram: OK\n")
        except Exception as e:
            results["instagram"] = "error"
            errors["instagram"] = str(e)
            yield emit(f"Instagram: ERROR — {e}\n")
    elif mode == "publicar":
        results["instagram"] = "skipped"
        yield emit("Instagram: SKIPPED\n")
    else:
        results["instagram"] = "skipped"
        yield emit("Instagram: SKIPPED (scheduling no disponible via API)\n")

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
            "scheduled_for": yt_dt.isoformat(),
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


def build_ui():
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    default_time = f"{DEFAULT_PUBLISH_HOUR:02d}:{DEFAULT_PUBLISH_MINUTE:02d}"
    day_name, today_preset = get_today_preset()
    dia_es = DIAS_ES[today.weekday()]
    saved_mode = load_mode()

    CHIPS_PUBLICAR  = ["YouTube", "TikTok", "Instagram"]
    CHIPS_PROGRAMAR = ["YouTube", "TikTok"]

    with gr.Blocks(title="Shorts Uploader") as app:

        gr.HTML(f"""
        <div id="header-row">
            <h1>Shorts Uploader</h1>
            <p>{dia_es} {today_str} &nbsp;|&nbsp; {today_preset['label'].split('—')[1].strip()}</p>
        </div>
        """)

        mode_state = gr.State(saved_mode)

        with gr.Row(equal_height=False):

            # ---- Columna izquierda: form fields ----
            with gr.Column(scale=3, min_width=300):

                with gr.Row():
                    video_dropdown = gr.Dropdown(
                        choices=get_video_choices(),
                        label="",
                        interactive=True,
                        scale=5,
                    )
                    refresh_btn = gr.Button("↻", size="sm", scale=1, min_width=48)

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
            with gr.Column(scale=2, min_width=200):

                gr.HTML('<p class="section-label">Modo de publicacion</p>')
                with gr.Tabs(selected=saved_mode) as tabs:
                    with gr.TabItem("Publicar ahora", id="publicar") as tab_publicar:
                        gr.Markdown(
                            "<small>Instagram ahora · YouTube en ~15 min · TikTok en ~30 min</small>",
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
                        gr.Markdown("<small>Instagram no se programa via API.</small>")

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
    app.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True, theme=THEME, css=CHIP_CSS)
