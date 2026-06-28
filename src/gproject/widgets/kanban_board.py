"""Vista Kanban agrupada por estado."""

from __future__ import annotations

from rich.segment import Segment
from rich.style import Style
from textual.binding import Binding
from textual.geometry import Size
from textual.message import Message
from textual.scroll_view import ScrollView
from textual.strip import Strip

from gproject.models import PRIORIDAD_COLOR, Tarea

HEADER_H = 2
COLUMNAS = (
    ("todo", "Pendiente"),
    ("doing", "En progreso"),
    ("done", "Hecho"),
)
COL_BG = "#1a1b26"
COL_HEADER = "#24283b"
COL_MUTED = "#565f89"
COL_TEXT = "#c0caf5"
COL_SEL = "#2d3343"
COL_BORDER = "#3b4261"


class KanbanView(ScrollView):
    """Tablero simple de tres columnas basado en ``Tarea.estado``."""

    can_focus = True

    BINDINGS = [
        Binding("up,k", "cursor(-1)", "Subir", show=False),
        Binding("down,j", "cursor(1)", "Bajar", show=False),
        Binding("left", "columna(-1)", "Columna izq", show=False),
        Binding("right", "columna(1)", "Columna der", show=False),
        Binding("space", "alternar_estado", "Estado", show=False),
    ]

    class TareaResaltada(Message):
        def __init__(self, tarea: Tarea | None) -> None:
            self.tarea = tarea
            super().__init__()

    class AlternarEstado(Message):
        def __init__(self, tarea: Tarea) -> None:
            self.tarea = tarea
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self.tareas: list[Tarea] = []
        self.por_estado: dict[str, list[Tarea]] = {estado: [] for estado, _ in COLUMNAS}
        self.columna = 0
        self.cursor = 0

    def cargar(self, tareas: list[Tarea]) -> None:
        actual_id = self.tarea_actual.id if self.tarea_actual else None
        self.tareas = tareas
        self.por_estado = {estado: [] for estado, _ in COLUMNAS}
        for tarea in tareas:
            self.por_estado.setdefault(tarea.estado, []).append(tarea)
        for estado in self.por_estado:
            self.por_estado[estado].sort(key=lambda t: (t.orden, t.id))
        self._ajustar_cursor()
        if actual_id is not None:
            self.seleccionar_tarea(actual_id)
        self._actualizar_virtual_size()
        self.refresh()

    @property
    def tarea_actual(self) -> Tarea | None:
        tareas = self._columna_actual()
        if 0 <= self.cursor < len(tareas):
            return tareas[self.cursor]
        return None

    def seleccionar_tarea(self, tarea_id: int) -> None:
        for col, (estado, _) in enumerate(COLUMNAS):
            for idx, tarea in enumerate(self.por_estado.get(estado, [])):
                if tarea.id == tarea_id:
                    self.columna = col
                    self.cursor = idx
                    self._seleccion_cambiada()
                    return

    def _columna_actual(self) -> list[Tarea]:
        estado = COLUMNAS[self.columna][0]
        return self.por_estado.get(estado, [])

    def _ajustar_cursor(self) -> None:
        self.columna = max(0, min(self.columna, len(COLUMNAS) - 1))
        tareas = self._columna_actual()
        self.cursor = max(0, min(self.cursor, len(tareas) - 1)) if tareas else 0

    def _actualizar_virtual_size(self) -> None:
        alto = max((len(self.por_estado.get(e, [])) for e, _ in COLUMNAS), default=0)
        self.virtual_size = Size(max(self.size.width, 72), alto + HEADER_H)

    def on_resize(self) -> None:
        self._actualizar_virtual_size()

    def render_line(self, y: int) -> Strip:
        ancho = self.size.width
        col_w = max(ancho // len(COLUMNAS), 24)
        row = int(self.scroll_offset.y) + y - HEADER_H
        segmentos: list[Segment] = []
        for idx, (estado, titulo) in enumerate(COLUMNAS):
            tareas = self.por_estado.get(estado, [])
            if y == 0:
                texto = f" {titulo} ({len(tareas)})"
                estilo = Style(color=COL_TEXT, bgcolor=COL_HEADER, bold=idx == self.columna)
            elif y == 1:
                texto = "─" * (col_w - 1)
                estilo = Style(color=COL_BORDER, bgcolor=COL_BG)
            elif 0 <= row < len(tareas):
                texto, estilo = self._render_tarjeta(tareas[row], idx, row, col_w)
            else:
                texto = ""
                estilo = Style(bgcolor=COL_BG)
            segmentos.append(Segment(texto[:col_w - 1].ljust(col_w - 1), estilo))
            segmentos.append(Segment("│", Style(color=COL_BORDER, bgcolor=COL_BG)))
        return Strip(segmentos)

    def _render_tarjeta(
        self,
        tarea: Tarea,
        columna: int,
        fila: int,
        ancho: int,
    ) -> tuple[str, Style]:
        seleccionada = columna == self.columna and fila == self.cursor
        titulo = tarea.titulo
        if tarea.parent_id is not None:
            titulo = f"↳ {titulo}"
        progreso = "" if tarea.es_hito else f" {tarea.progreso}%"
        texto = f" {tarea.icono} {titulo}{progreso}"
        if tarea.etiquetas:
            texto += "  " + " ".join(f"#{e.nombre}" for e in tarea.etiquetas[:2])
        color = "#5c6370" if tarea.estado == "done" else PRIORIDAD_COLOR.get(
            tarea.prioridad, COL_TEXT
        )
        estilo = Style(color=color, bgcolor=COL_SEL if seleccionada else COL_BG)
        return texto[:ancho - 1], estilo

    def action_cursor(self, delta: int) -> None:
        tareas = self._columna_actual()
        if not tareas:
            return
        self.cursor = max(0, min(self.cursor + delta, len(tareas) - 1))
        self._seleccion_cambiada()

    def action_columna(self, delta: int) -> None:
        self.columna = max(0, min(self.columna + delta, len(COLUMNAS) - 1))
        self._ajustar_cursor()
        self._seleccion_cambiada()

    def action_alternar_estado(self) -> None:
        tarea = self.tarea_actual
        if tarea and not tarea.es_hito:
            self.post_message(self.AlternarEstado(tarea))

    def _seleccion_cambiada(self) -> None:
        self.post_message(self.TareaResaltada(self.tarea_actual))
        self.refresh()
