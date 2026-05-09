from datetime import date

PRESETS = {
    "lunes": {
        "label": "Lunes — Humor situacional (laburo remoto / tech)",
        "hashtags": "#ingenieria #sistemas #universidad #facultad #programacion #frannoni",
        "keywords": "ingenieria sistemas utn, humor programador, vida universitaria argentina, junior developer argentina, frannoni",
    },
    "martes": {
        "label": "Martes — Dato shock / Como funciona X",
        "hashtags": "#ingenieria #sistemas #programacion #tecnologia #facultad #frannoni",
        "keywords": "ingenieria sistemas utn, como funciona tecnologia, curiosidades tech, programacion argentina, frannoni",
    },
    "miercoles": {
        "label": "Miercoles — Italia / vida afuera / argentino en Europa",
        "hashtags": "#trabajoremoto #italia #ingenieria #programacion #remotework #frannoni",
        "keywords": "trabajo remoto programador argentina, vivir en italia argentino, sueldo en euros, junior developer remoto, frannoni",
    },
    "jueves": {
        "label": "Jueves — Tech experiencial / producto con angulo personal",
        "hashtags": "#ingenieria #programacion #tech #sistemas #dev #frannoni",
        "keywords": "herramientas programador 2026, setup trabajo remoto, productos tech baratos, ingenieria sistemas utn, frannoni",
    },
    "viernes": {
        "label": "Viernes — Facultad / universidad / carrera de ingenieria",
        "hashtags": "#ingenieria #utn #universidad #facultad #examen #frannoni",
        "keywords": "ingenieria sistemas utn, como aprobar materias ingenieria, vida universitaria argentina, primer año ingenieria, frannoni",
    },
    "sabado": {
        "label": "Sabado — Corte del largo de la semana",
        "hashtags": "#ingenieria #sistemas #universidad #programacion #facultad #frannoni",
        "keywords": "ingenieria sistemas utn, vida universitaria argentina, programacion argentina, trabajo remoto programador, frannoni",
    },
    "domingo": {
        "label": "Domingo — Corte del largo (o short original)",
        "hashtags": "#ingenieria #sistemas #universidad #programacion #facultad #frannoni",
        "keywords": "ingenieria sistemas utn, vida universitaria argentina, programacion argentina, trabajo remoto programador, frannoni",
    },
}

_DAY_MAP = {0: "lunes", 1: "martes", 2: "miercoles", 3: "jueves", 4: "viernes", 5: "sabado", 6: "domingo"}


def get_today_preset() -> tuple[str, dict]:
    """Retorna (day_name, preset) para hoy."""
    day_name = _DAY_MAP[date.today().weekday()]
    return day_name, PRESETS[day_name]


def preset_labels() -> list[str]:
    return [v["label"] for v in PRESETS.values()]


def preset_by_label(label: str) -> dict:
    for preset in PRESETS.values():
        if preset["label"] == label:
            return preset
    return list(PRESETS.values())[0]
