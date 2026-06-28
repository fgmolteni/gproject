"""Modelos de dominio y constantes compartidas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

# --- Constantes de presentación -------------------------------------------------

ESTADOS = ("todo", "doing", "done")

ESTADO_ICONO = {
    "todo": "☐",
    "doing": "◐",
    "done": "☑",
}

PRIORIDADES = ("alta", "media", "baja")

PRIORIDAD_COLOR = {
    "alta": "#ff5c57",
    "media": "#f3a712",
    "baja": "#43c59e",
}


# --- Conversión de fechas -------------------------------------------------------

def parse_fecha(value: str | None) -> date | None:
    """Convierte una cadena ISO (YYYY-MM-DD) en ``date`` o ``None``."""
    if not value:
        return None
    return date.fromisoformat(value)


def fecha_iso(value: date | None) -> str | None:
    """Serializa un ``date`` a cadena ISO o ``None``."""
    return value.isoformat() if value else None


# --- Modelos --------------------------------------------------------------------

@dataclass
class Proyecto:
    id: int
    nombre: str
    descripcion: str = ""
    color: str = "#4a9eff"
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    archivado: bool = False
    creado_en: str = ""


@dataclass
class Tarea:
    id: int
    proyecto_id: int
    titulo: str
    parent_id: int | None = None
    descripcion: str = ""
    fecha_inicio: date | None = None
    duracion_dias: int = 1
    progreso: int = 0
    estado: str = "todo"
    prioridad: str = "media"
    es_hito: bool = False
    orden: int = 0
    creado_en: str = ""
    completado_en: str | None = None

    # Campos auxiliares poblados por la UI (no se persisten aquí)
    etiquetas: list["Etiqueta"] = field(default_factory=list)

    @property
    def duracion_efectiva(self) -> int:
        """Número de días/celdas que ocupa la barra (los hitos ocupan 1)."""
        if self.es_hito:
            return 1
        return max(self.duracion_dias, 1)

    @property
    def fecha_fin(self) -> date | None:
        """Último día inclusive que abarca la tarea."""
        if self.fecha_inicio is None:
            return None
        return self.fecha_inicio + timedelta(days=self.duracion_efectiva - 1)

    @property
    def icono(self) -> str:
        if self.es_hito:
            return "◆"
        return ESTADO_ICONO.get(self.estado, "☐")


@dataclass
class Etiqueta:
    id: int
    nombre: str
    color: str = "#8a8a8a"


@dataclass
class Dependencia:
    tarea_id: int
    depende_de_id: int
