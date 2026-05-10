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
):
    from config import PENDING_DIR

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
        yt_dt = now + timedelta(minutes=10)
        tt_dt = now + timedelta(minutes=25)
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

    if mode == "publicar":
        yield emit(f"Modo: PUBLICAR — Instagram ahora, YouTube en ~10min, TikTok en ~25min\n")
    else:
        yield emit(f"Modo: PROGRAMAR — {pub_time} ART del {pub_date}\n")
    yield emit(f"Video: {video_name}\n")
    yield emit("---\n")

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

    yield emit("TikTok: subiendo...\n")
    try:
        asyncio.run(tt_upload(str(video_path), title, description, hashtags, tt_dt))
        results["tiktok"] = "ok"
        yield emit("TikTok: OK\n")
    except Exception as e:
        results["tiktok"] = "error"
        errors["tiktok"] = str(e)
        yield emit(f"TikTok: ERROR — {e}\n")

    if mode == "publicar":
        yield emit("Instagram: subiendo...\n")
        try:
            asyncio.run(ig_upload(str(video_path), caption, ig_dt))
            results["instagram"] = "ok"
            yield emit("Instagram: OK\n")
        except Exception as e:
            results["instagram"] = "error"
            errors["instagram"] = str(e)
            yield emit(f"Instagram: ERROR — {e}\n")
    else:
        results["instagram"] = "skipped"
        yield emit("Instagram: SKIPPED (scheduling no disponible via API)\n")

    yt_ok = results["youtube"] == "ok"
    tt_ok = results["tiktok"] == "ok"

    # Auto-guardar hashtags/keywords si el usuario los modifico
    day = day_from_label(preset_label)
    save_preset_override(day, hashtags, keywords_raw)

    if yt_ok and tt_ok:
        metadata = {
            "video": video_name,
            "title": title,
            "description": description,
            "hashtags": hashtags,
            "keywords": keywords,
            "category_id": category_id,
            "language": language,
            "mode": mode,
            "scheduled_for": yt_dt.isoformat(),
            "uploaded_at": now.isoformat(),
            "results": results,
        }
        move_to_finalized(video_path, metadata)
        yield emit("\nFinalizado: video movido a ~/shorts-uploader/finalized/\n")
    else:
        yield emit("\nHubo errores en YouTube o TikTok. El video NO fue movido a finalized.\n")
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

    with gr.Blocks(title="Shorts Uploader") as app:

        gr.Markdown("# Shorts Uploader")
        gr.Markdown(f"**Hoy:** {dia_es} {today_str} — {today_preset['label'].split('—')[1].strip()}")

        with gr.Row():
            video_dropdown = gr.Dropdown(
                choices=get_video_choices(),
                label="Video (desde ~/shorts-uploader/pending/)",
                interactive=True,
            )
            refresh_btn = gr.Button("Actualizar lista", size="sm")

        gr.Markdown("### Contenido")
        title_input = gr.Textbox(label="Titulo", placeholder="Titulo del video")
        desc_input = gr.Textbox(label="Descripcion", lines=4, placeholder="Descripcion completa")

        gr.Markdown("### Hashtags y Keywords")
        preset_dropdown = gr.Dropdown(
            choices=preset_labels(),
            value=today_preset["label"],
            label="Preset del dia (se puede cambiar)",
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

        gr.Markdown("### YouTube")
        with gr.Row():
            category_input = gr.Dropdown(
                choices=list(YT_CATEGORIES.keys()),
                value="Education (27)",
                label="Categoria",
            )
            language_input = gr.Dropdown(
                choices=["es", "en", "it"],
                value="es",
                label="Idioma",
            )

        gr.Markdown("### Modo de publicacion")
        mode_state = gr.State(saved_mode)

        with gr.Tabs() as tabs:
            with gr.TabItem("Publicar", id="publicar") as tab_publicar:
                gr.Markdown(
                    "El contenido sera publicado lo antes posible:  \n"
                    "**Instagram** — ahora  |  **YouTube** — en ~10 min  |  **TikTok** — en ~25 min"
                )
            with gr.TabItem("Programar publicacion", id="programar") as tab_programar:
                with gr.Row():
                    date_input = gr.Textbox(label="Fecha (YYYY-MM-DD)", value=today_str)
                    time_input = gr.Dropdown(
                        choices=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)],
                        value=default_time,
                        label="Hora ART",
                    )
                gr.Markdown("*Instagram no se sube en modo Programar (limitacion de API de Meta).*")

        run_btn = gr.Button("PUBLICAR EN LAS 3 PLATAFORMAS", variant="primary")
        log_output = gr.Textbox(label="Log", lines=15, interactive=False)

        def on_select_publicar():
            save_mode("publicar")
            return "publicar"

        def on_select_programar():
            save_mode("programar")
            return "programar"

        tab_publicar.select(fn=on_select_publicar, outputs=mode_state)
        tab_programar.select(fn=on_select_programar, outputs=mode_state)

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
                keywords_input, preset_dropdown, category_input, language_input, date_input, time_input,
            ],
            outputs=log_output,
        )

    return app


if __name__ == "__main__":
    app = build_ui()
    app.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
