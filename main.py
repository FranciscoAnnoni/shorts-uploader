import gradio as gr
import threading
from datetime import datetime, date, time
from pathlib import Path
import pytz

from config import DEFAULT_PUBLISH_HOUR, DEFAULT_PUBLISH_MINUTE, YT_CATEGORIES, YT_DEFAULT_LANGUAGE, YT_DEFAULT_CATEGORY
from utils import get_pending_videos, build_caption, move_to_finalized, get_schedule_datetime
from uploaders.youtube import upload as yt_upload
from uploaders.tiktok import upload as tt_upload
from uploaders.instagram import upload as ig_upload

ART_TZ = pytz.timezone("America/Argentina/Buenos_Aires")


def get_video_choices() -> list[str]:
    return [v.name for v in get_pending_videos()]


def run_upload(
    video_name: str,
    title: str,
    description: str,
    hashtags: str,
    keywords_raw: str,
    category_label: str,
    language: str,
    pub_date: str,
    pub_time: str,
):
    """
    Generador: yield strings de log para mostrar en la GUI en tiempo real.
    """
    from config import PENDING_DIR

    video_path = PENDING_DIR / video_name
    if not video_path.exists():
        yield f"Error: no se encontro el video en {video_path}"
        return

    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    category_id = YT_CATEGORIES.get(category_label, YT_DEFAULT_CATEGORY)
    caption = build_caption(title, description, hashtags)
    schedule_dt = get_schedule_datetime(pub_date, pub_time)

    results = {"youtube": None, "tiktok": None, "instagram": None}
    errors = {}

    yield f"Programando para las {pub_time} ART del {pub_date}\n"
    yield f"Video: {video_name}\n"
    yield "---\n"

    # YouTube
    yield "YouTube: subiendo...\n"
    try:
        import asyncio
        asyncio.run(yt_upload(
            str(video_path), title, description, hashtags,
            keywords, language, category_id, schedule_dt
        ))
        results["youtube"] = "ok"
        yield "YouTube: OK\n"
    except Exception as e:
        results["youtube"] = "error"
        errors["youtube"] = str(e)
        yield f"YouTube: ERROR — {e}\n"

    # TikTok
    yield "TikTok: subiendo...\n"
    try:
        import asyncio
        asyncio.run(tt_upload(str(video_path), title, description, hashtags, schedule_dt))
        results["tiktok"] = "ok"
        yield "TikTok: OK\n"
    except Exception as e:
        results["tiktok"] = "error"
        errors["tiktok"] = str(e)
        yield f"TikTok: ERROR — {e}\n"

    # Instagram
    yield "Instagram: subiendo...\n"
    try:
        import asyncio
        asyncio.run(ig_upload(str(video_path), caption, schedule_dt))
        results["instagram"] = "ok"
        yield "Instagram: OK\n"
    except Exception as e:
        results["instagram"] = "error"
        errors["instagram"] = str(e)
        yield f"Instagram: ERROR — {e}\n"

    # Mover a finalized si las 3 tuvieron exito
    if all(v == "ok" for v in results.values()):
        metadata = {
            "video": video_name,
            "title": title,
            "description": description,
            "hashtags": hashtags,
            "keywords": keywords,
            "category_id": category_id,
            "language": language,
            "scheduled_for": schedule_dt.isoformat(),
            "uploaded_at": datetime.now(ART_TZ).isoformat(),
            "results": results,
        }
        move_to_finalized(video_path, metadata)
        yield f"\nFinalizado: video movido a ~/shorts-uploader/finalized/\n"
    else:
        yield f"\nHubo errores en algunas plataformas. El video NO fue movido a finalized.\n"
        for platform, err in errors.items():
            yield f"  {platform}: {err}\n"


def build_ui():
    today = date.today().strftime("%Y-%m-%d")
    default_time = f"{DEFAULT_PUBLISH_HOUR:02d}:{DEFAULT_PUBLISH_MINUTE:02d}"

    with gr.Blocks(title="Shorts Uploader") as app:
        gr.Markdown("# Shorts Uploader")

        with gr.Row():
            video_dropdown = gr.Dropdown(
                choices=get_video_choices(),
                label="Video (desde ~/shorts-uploader/pending/)",
                interactive=True,
            )
            refresh_btn = gr.Button("Actualizar lista", size="sm")

        gr.Markdown("### YouTube")
        title_input = gr.Textbox(label="Titulo", placeholder="Titulo del video")
        desc_input = gr.Textbox(label="Descripcion", lines=5, placeholder="Descripcion completa")
        hashtags_input = gr.Textbox(label="Hashtags (se replica a IG y TikTok)", placeholder="#tech #programacion #trabajoremoto")
        keywords_input = gr.Textbox(label="Keywords YouTube (separadas por coma)", placeholder="programacion, trabajo remoto, argentina")
        with gr.Row():
            category_input = gr.Dropdown(choices=list(YT_CATEGORIES.keys()), value="Education (27)", label="Categoria")
            language_input = gr.Dropdown(choices=["es", "en", "it"], value="es", label="Idioma")

        gr.Markdown("### Programar publicacion")
        with gr.Row():
            date_input = gr.Textbox(label="Fecha (YYYY-MM-DD)", value=today)
            time_input = gr.Dropdown(
                choices=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)],
                value=default_time,
                label="Hora ART",
            )

        run_btn = gr.Button("SUBIR A LAS 3 PLATAFORMAS", variant="primary")
        log_output = gr.Textbox(label="Log", lines=15, interactive=False)

        refresh_btn.click(fn=lambda: gr.Dropdown(choices=get_video_choices()), outputs=video_dropdown)
        run_btn.click(
            fn=run_upload,
            inputs=[video_dropdown, title_input, desc_input, hashtags_input,
                    keywords_input, category_input, language_input, date_input, time_input],
            outputs=log_output,
        )

    return app


if __name__ == "__main__":
    app = build_ui()
    app.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
