from datetime import date
import json
from pathlib import Path

# Primeros 5 hashtags = prioritarios (limite de IG y TikTok)
# Los siguientes son bonus para YouTube description
PRESETS_DEFAULT = {
    "lunes": {
        "label": "Lunes — Humor situacional (laburo remoto / tech)",
        "hashtags": "#programacion #ingenieria #humor #argentina #trabajoremoto #developer #junior #utn #dev #frannoni",
        "keywords": "humor programador, trabajo remoto argentina, junior developer argentina, programacion argentina, ingenieria sistemas utn, vida remota, frannoni",
    },
    "martes": {
        "label": "Martes — Dato shock / Como funciona X",
        "hashtags": "#programacion #tecnologia #comoFunciona #ingenieria #curiosidades #tech #IA #ciencia #datos #frannoni",
        "keywords": "como funciona la tecnologia, curiosidades tech, programacion argentina, ingenieria sistemas, inteligencia artificial 2026, dato curioso tech, frannoni",
    },
    "miercoles": {
        "label": "Miercoles — Italia / vida afuera / argentino en Europa",
        "hashtags": "#trabajoremoto #italia #argentina #programacion #ingenieria #remotework #europa #sueldo #ingeniero #frannoni",
        "keywords": "trabajo remoto programador argentina, vivir en italia argentino, sueldo argentino en euros, ingeniero argentino europa, trabajo remoto 2026, frannoni",
    },
    "jueves": {
        "label": "Jueves — Tech experiencial / producto con angulo personal",
        "hashtags": "#tech #programacion #setup #herramientas #ingenieria #gadgets #trabajoremoto #productividad #dev #frannoni",
        "keywords": "herramientas programador 2026, setup trabajo remoto, productos tech baratos, gadgets programador, ingenieria sistemas, productividad developer, frannoni",
    },
    "viernes": {
        "label": "Viernes — Facultad / universidad / carrera de ingenieria",
        "hashtags": "#utn #ingenieria #universidad #programacion #argentina #facultad #estudiantes #sistemas #carrera #frannoni",
        "keywords": "ingenieria sistemas utn, como aprobar materias ingenieria, primer trabajo programador argentina, vida universitaria argentina, consejo universitario ingenieria, frannoni",
    },
    "sabado": {
        "label": "Sabado — Corte del largo de la semana",
        "hashtags": "#programacion #ingenieria #argentina #trabajoremoto #italia #tech #developer #utn #sistemas #frannoni",
        "keywords": "programacion argentina, ingenieria sistemas utn, trabajo remoto argentina, vida en italia argentino, developer junior, frannoni",
    },
    "domingo": {
        "label": "Domingo — Corte del largo (o short original)",
        "hashtags": "#programacion #ingenieria #argentina #trabajoremoto #italia #tech #developer #utn #sistemas #frannoni",
        "keywords": "programacion argentina, ingenieria sistemas utn, trabajo remoto argentina, vida en italia argentino, developer junior, frannoni",
    },
}

_CUSTOM_FILE = Path(__file__).parent / "presets-custom.json"


def _load_custom() -> dict:
    try:
        return json.loads(_CUSTOM_FILE.read_text())
    except Exception:
        return {}


def _save_custom(custom: dict):
    _CUSTOM_FILE.write_text(json.dumps(custom, indent=2, ensure_ascii=False))


def get_preset(day: str) -> dict:
    """Retorna el preset para el dia, con overrides del usuario si existen."""
    default = PRESETS_DEFAULT.get(day, PRESETS_DEFAULT["lunes"]).copy()
    custom = _load_custom().get(day, {})
    default.update(custom)
    return default


def save_preset_override(day: str, hashtags: str, keywords: str):
    """Guarda hashtags/keywords personalizados para un dia especifico."""
    custom = _load_custom()
    if day not in custom:
        custom[day] = {}
    custom[day]["hashtags"] = hashtags
    custom[day]["keywords"] = keywords
    _save_custom(custom)


_DAY_MAP = {0: "lunes", 1: "martes", 2: "miercoles", 3: "jueves", 4: "viernes", 5: "sabado", 6: "domingo"}


def get_today_preset() -> tuple[str, dict]:
    day_name = _DAY_MAP[date.today().weekday()]
    return day_name, get_preset(day_name)


def preset_labels() -> list[str]:
    return [get_preset(day)["label"] for day in _DAY_MAP.values()]


def preset_by_label(label: str) -> dict:
    for day in _DAY_MAP.values():
        preset = get_preset(day)
        if preset["label"] == label:
            return preset
    return get_preset("lunes")


def day_from_label(label: str) -> str:
    for day in _DAY_MAP.values():
        if get_preset(day)["label"] == label:
            return day
    return "lunes"
