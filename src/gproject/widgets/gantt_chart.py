"""Widget central: panel de tareas + diagrama de Gantt, renderizado por líneas.

El panel izquierdo (árbol de tareas) queda congelado mientras la línea de tiempo
de la derecha se desplaza con ←/→ y hace zoom con +/-. Cada fila del árbol se alinea
exactamente con su barra porque ambas partes se dibujan en la misma línea.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from rich.segment import Segment
from rich.style import Style
from textual.binding import Binding
from textual.geometry import Size
from textual.message import Message
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip

from gproject.models import PRIORIDAD_COLOR, Dependencia, Tarea
from gproject.scheduling import calcular_cpm

HEADER_H = 2
PANEL_ANCHO = 32

# (etiqueta, días por columna, ancho de columna en celdas)
ZOOM_NIVELES = [("Día", 1, 3), ("Semana", 7, 5), ("Mes", 30, 9)]

MESES = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct",
         "nov", "dic"]

COL_HOY = "#e0af68"
COL_CRITICA = "#ff5c57"
COL_GRID = "#3b4252"
COL_CONECTOR = "#7aa2f7"
COL_SELECCION = "#2d3343"
COL_PANEL_BG = "#1a1b26"

ESTADO_BAR = {"todo": "#6b7394", "doing": "#f3a712", "done": "#43c59e"}


@dataclass
class Fila:
    tarea: Tarea
    nivel: int
    tiene_hijos: bool
    expandida: bool
    progreso: int
    critica: bool


class GanttView(ScrollView):
    """Vista combinada de árbol de tareas y diagrama de Gantt."""

    can_focus = True

    BINDINGS = [
        Binding("up,k", "cursor(-1)", "Subir", show=False),
        Binding("down,j", "cursor(1)", "Bajar", show=False),
        Binding("left", "desplazar(-4)", "◄ línea de tiempo", show=False),
        Binding("right", "desplazar(4)", "línea de tiempo ►", show=False),
        Binding("z", "ciclar_zoom", "Zoom Día/Sem/Mes", show=True),
        Binding("plus,equals_sign,=", "zoom(-1)", "Zoom +", show=False),
        Binding("minus", "zoom(1)", "Zoom -", show=False),
        Binding("c", "colapsar", "Colapsar", show=False),
        Binding("space", "alternar_estado", "Estado", show=False),
    ]

    cursor: reactive[int] = reactive(0)
    nivel: reactive[int] = reactive(0)
    desplazamiento: reactive[int] = reactive(0)

    class TareaResaltada(Message):
        def __init__(self, tarea: Tarea | None) -> None:
            self.tarea = tarea
            super().__init__()

    class AlternarEstado(Message):
        def __init__(self, tarea: Tarea) -> None:
            self.tarea = tarea
            super().__init__()

    class ZoomCambiado(Message):
        def __init__(self, nivel: int) -> None:
            self.nivel = nivel
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self.tareas: list[Tarea] = []
        self.dependencias: list[Dependencia] = []
        self.colapsados: set[int] = set()
        self.filas: list[Fila] = []
        self._cpm: dict = {}
        self._conectores: dict[int, dict[int, tuple[str, Style]]] = {}
        self._origen: date = date.today()
        self._total_px: int = 0

    # -- Carga de datos ----------------------------------------------------------

    def cargar(self, tareas: list[Tarea], dependencias: list[Dependencia]) -> None:
        self.tareas = tareas
        self.dependencias = dependencias
        self._cpm = calcular_cpm(tareas, dependencias)
        self._reconstruir()

    @property
    def _dpc(self) -> int:
        return ZOOM_NIVELES[self.nivel][1]

    @property
    def _cw(self) -> int:
        return ZOOM_NIVELES[self.nivel][2]

    @property
    def nivel_zoom_label(self) -> str:
        return ZOOM_NIVELES[self.nivel][0]

    @property
    def tarea_actual(self) -> Tarea | None:
        if 0 <= self.cursor < len(self.filas):
            return self.filas[self.cursor].tarea
        return None

    # -- Construcción del modelo de filas ---------------------------------------

    def _reconstruir(self) -> None:
        hijos: dict[int | None, list[Tarea]] = {}
        for t in self.tareas:
            hijos.setdefault(t.parent_id, []).append(t)
        for lst in hijos.values():
            lst.sort(key=lambda t: (t.orden, t.id))

        progreso_cache: dict[int, int] = {}

        def progreso_de(t: Tarea) -> int:
            sub = hijos.get(t.id)
            if not sub:
                return t.progreso
            total = sum(s.duracion_efectiva for s in sub) or 1
            val = sum(progreso_de(s) * s.duracion_efectiva for s in sub) / total
            progreso_cache[t.id] = round(val)
            return progreso_cache[t.id]

        filas: list[Fila] = []

        def agregar(parent_id: int | None, nivel: int) -> None:
            for t in hijos.get(parent_id, []):
                tiene = bool(hijos.get(t.id))
                expandida = t.id not in self.colapsados
                prog = progreso_de(t)
                critica = self._cpm.get(t.id).critica if t.id in self._cpm else False
                filas.append(Fila(t, nivel, tiene, expandida, prog, critica))
                if tiene and expandida:
                    agregar(t.id, nivel + 1)

        agregar(None, 0)
        self.filas = filas

        fechas_ini = [t.fecha_inicio for t in self.tareas if t.fecha_inicio]
        fechas_fin = [t.fecha_fin for t in self.tareas if t.fecha_fin]
        self._origen = min(fechas_ini) if fechas_ini else date.today()
        fin = max(fechas_fin) if fechas_fin else self._origen
        n_cols = self._col(fin) + 1
        self._total_px = max(n_cols * self._cw, 1)

        self._construir_conectores()
        if self.cursor >= len(self.filas):
            self.cursor = max(len(self.filas) - 1, 0)
        self._actualizar_virtual_size()
        self.refresh()

    def _actualizar_virtual_size(self) -> None:
        ancho = max(self.size.width, PANEL_ANCHO + 10)
        self.virtual_size = Size(ancho, len(self.filas) + HEADER_H)

    def on_resize(self) -> None:
        self._actualizar_virtual_size()

    # -- Geometría temporal ------------------------------------------------------

    def _col(self, f: date) -> int:
        return (f - self._origen).days // self._dpc

    def _px_inicio(self, f: date) -> int:
        return self._col(f) * self._cw

    def _px_fin(self, f: date) -> int:
        return (self._col(f) + 1) * self._cw - 1

    # -- Conectores de dependencias ---------------------------------------------

    def _construir_conectores(self) -> None:
        self._conectores = {}
        fila_de: dict[int, int] = {f.tarea.id: i for i, f in enumerate(self.filas)}
        px_ini: dict[int, int] = {}
        px_fin: dict[int, int] = {}
        for f in self.filas:
            if f.tarea.fecha_inicio:
                px_ini[f.tarea.id] = self._px_inicio(f.tarea.fecha_inicio)
                px_fin[f.tarea.id] = self._px_fin(f.tarea.fecha_fin)

        estilo = Style(color=COL_CONECTOR)
        for dep in self.dependencias:
            succ, pred = dep.tarea_id, dep.depende_de_id
            if succ not in fila_de or pred not in fila_de:
                continue
            if pred not in px_fin or succ not in px_ini:
                continue
            r_pred, r_succ = fila_de[pred], fila_de[succ]
            x_pred, x_succ = px_fin[pred], px_ini[succ]
            canal = min(x_pred + 1, max(x_succ - 1, 0))
            canal = max(canal, x_pred + 1)
            lo, hi = sorted((r_pred, r_succ))
            # tramo vertical en el canal
            for r in range(lo + 1, hi):
                self._poner(r, canal, "│", estilo)
            # esquina y tramo en la fila del predecesor
            for x in range(x_pred + 1, canal):
                self._poner(r_pred, x, "─", estilo)
            self._poner(r_pred, canal, "┐" if r_succ > r_pred else "┘", estilo)
            # tramo y flecha en la fila del sucesor
            for x in range(canal + 1, x_succ):
                self._poner(r_succ, x, "─", estilo)
            self._poner(r_succ, canal, "└" if r_succ > r_pred else "┌", estilo)
            if x_succ - 1 >= canal:
                self._poner(r_succ, max(x_succ - 1, canal), "►", estilo)

    def _poner(self, fila: int, col: int, ch: str, estilo: Style) -> None:
        if col < 0:
            return
        self._conectores.setdefault(fila, {})[col] = (ch, estilo)

    # -- Render ------------------------------------------------------------------

    def render_line(self, y: int) -> Strip:
        ancho = self.size.width
        tl_w = max(ancho - PANEL_ANCHO, 0)
        if y < HEADER_H:
            izq, der = self._render_header(y, tl_w)
        else:
            idx = int(self.scroll_offset.y) + (y - HEADER_H)
            if idx >= len(self.filas):
                return Strip([Segment(" " * ancho, Style(bgcolor=COL_PANEL_BG))])
            izq = self._render_panel(self.filas[idx], idx)
            der = self._render_timeline(self.filas[idx], idx, tl_w)
        return Strip(izq + der)

    def _render_panel(self, fila: Fila, idx: int) -> list[Segment]:
        t = fila.tarea
        sel = idx == self.cursor
        sangria = "  " * fila.nivel
        if fila.tiene_hijos:
            flecha = "▾ " if fila.expandida else "▸ "
        else:
            flecha = "  "
        izq_txt = f"{sangria}{flecha}{t.icono} {t.titulo}"
        der_txt = "" if t.es_hito else f"{fila.progreso:>3d}%"
        disponible = PANEL_ANCHO - len(der_txt) - 1
        if len(izq_txt) > disponible:
            izq_txt = izq_txt[: disponible - 1] + "…"
        linea = f" {izq_txt}".ljust(PANEL_ANCHO - len(der_txt)) + der_txt

        if t.estado == "done":
            fg = "#5c6370"
        elif fila.critica:
            fg = COL_CRITICA
        else:
            fg = PRIORIDAD_COLOR.get(t.prioridad, "#c8d0e0")
        bg = COL_SELECCION if sel else COL_PANEL_BG
        estilo = Style(color=fg, bgcolor=bg, bold=fila.tiene_hijos)
        return [Segment(linea[:PANEL_ANCHO].ljust(PANEL_ANCHO), estilo)]

    def _celdas_timeline(self, fila: Fila, idx: int) -> list[tuple[str, Style]]:
        """Celdas de la línea de tiempo de una fila, ancho completo (sin recorte)."""
        base = Style(bgcolor=COL_PANEL_BG)
        celdas: list[tuple[str, Style]] = [(" ", base)] * self._total_px

        # Grilla vertical: separa las columnas de tiempo para que cada unidad
        # (semana/mes) se lea como un bloque. Solo en Semana/Mes (en Día sería ruido).
        estilo_grilla = Style(color=COL_GRID, bgcolor=COL_PANEL_BG)
        hay_grilla = self.nivel >= 1
        if hay_grilla:
            for px in range(self._cw, self._total_px, self._cw):
                celdas[px] = ("│", estilo_grilla)

        # marcador de hoy
        hoy_px = self._px_inicio(date.today())
        if 0 <= hoy_px < self._total_px:
            celdas[hoy_px] = ("┊", Style(color=COL_HOY, bgcolor=COL_PANEL_BG))

        # conectores de dependencias de esta fila
        for col, (ch, st) in self._conectores.get(idx, {}).items():
            if 0 <= col < self._total_px:
                celdas[col] = (ch, Style(color=st.color, bgcolor=COL_PANEL_BG))

        # barra de la tarea
        t = fila.tarea
        if t.fecha_inicio:
            s = self._px_inicio(t.fecha_inicio)
            if t.es_hito:
                if 0 <= s < self._total_px:
                    celdas[s] = ("◆", Style(color=COL_CRITICA, bgcolor=COL_PANEL_BG))
            else:
                e = self._px_fin(t.fecha_fin)
                color = COL_CRITICA if fila.critica else ESTADO_BAR.get(t.estado, "#6b7394")
                ancho_barra = max(e - s + 1, 1)
                lleno = s + round(ancho_barra * fila.progreso / 100)
                estilo_barra = Style(color=color, bgcolor=COL_PANEL_BG)
                for px in range(s, e + 1):
                    if not (0 <= px < self._total_px):
                        continue
                    # Las fronteras internas de columna seccionan la barra en unidades.
                    if hay_grilla and px != s and px % self._cw == 0:
                        celdas[px] = ("│", estilo_grilla)
                    else:
                        ch = "█" if px < lleno else "░"
                        celdas[px] = (ch, estilo_barra)
        return celdas

    def _render_timeline(self, fila: Fila, idx: int, tl_w: int) -> list[Segment]:
        if tl_w <= 0:
            return []
        base = Style(bgcolor=COL_PANEL_BG)
        celdas = self._celdas_timeline(fila, idx)
        # recorte a la ventana visible
        ini = self.desplazamiento
        ventana = celdas[ini : ini + tl_w]
        if len(ventana) < tl_w:
            ventana += [(" ", base)] * (tl_w - len(ventana))
        return _a_segmentos(ventana)

    def _celdas_header_der(self, y: int) -> list[tuple[str, Style]]:
        """Celdas de la franja derecha de la cabecera, ancho completo (sin recorte)."""
        base = Style(color="#565f89", bgcolor="#24283b")
        titulo = Style(color="#7aa2f7", bgcolor="#24283b", bold=True)
        celdas: list[tuple[str, Style]] = [(" ", base)] * self._total_px
        n_cols = max(self._total_px // self._cw, 1)

        for c in range(n_cols):
            fecha_c = self._origen + timedelta(days=c * self._dpc)
            px = c * self._cw
            if y == 0:
                if c == 0 or fecha_c.day <= self._dpc:
                    etq = f"{MESES[fecha_c.month]} {str(fecha_c.year)[2:]}"
                    _escribir(celdas, px, etq, titulo)
            else:
                if self.nivel == 0:
                    etq = f"{fecha_c.day:>2d}"
                elif self.nivel == 1:
                    etq = f"{fecha_c.day}/{fecha_c.month}"
                else:
                    etq = MESES[fecha_c.month]
                _escribir(celdas, px, etq, base)

        hoy_px = self._px_inicio(date.today())
        if 0 <= hoy_px < self._total_px:
            celdas[hoy_px] = ("┊" if y == 1 else "▼", Style(color=COL_HOY, bgcolor="#24283b"))
        return celdas

    def _render_header(self, y: int, tl_w: int) -> tuple[list[Segment], list[Segment]]:
        if y == 0:
            izq = [Segment(" Tareas".ljust(PANEL_ANCHO),
                           Style(color="#c8d0e0", bgcolor="#24283b", bold=True))]
        else:
            izq = [Segment(" planificación".ljust(PANEL_ANCHO),
                           Style(color="#565f89", bgcolor="#24283b"))]
        if tl_w <= 0:
            return izq, []

        base = Style(color="#565f89", bgcolor="#24283b")
        celdas = self._celdas_header_der(y)
        ini = self.desplazamiento
        ventana = celdas[ini : ini + tl_w]
        if len(ventana) < tl_w:
            ventana += [(" ", base)] * (tl_w - len(ventana))
        return izq, _a_segmentos(ventana)

    # -- Acciones ----------------------------------------------------------------

    def watch_cursor(self) -> None:
        self._scroll_cursor_visible()
        self.post_message(self.TareaResaltada(self.tarea_actual))
        self.refresh()

    def watch_desplazamiento(self) -> None:
        self.refresh()

    def watch_nivel(self) -> None:
        self._reconstruir()

    def action_cursor(self, delta: int) -> None:
        if not self.filas:
            return
        self.cursor = max(0, min(self.cursor + delta, len(self.filas) - 1))

    def action_desplazar(self, delta: int) -> None:
        tl_w = max(self.size.width - PANEL_ANCHO, 1)
        maximo = max(self._total_px - tl_w, 0)
        self.desplazamiento = max(0, min(self.desplazamiento + delta, maximo))

    def action_zoom(self, delta: int) -> None:
        self.nivel = max(0, min(self.nivel + delta, len(ZOOM_NIVELES) - 1))
        self.post_message(self.ZoomCambiado(self.nivel))

    def action_ciclar_zoom(self) -> None:
        """Cicla Día → Semana → Mes → Día (tecla robusta en cualquier teclado)."""
        self.nivel = (self.nivel + 1) % len(ZOOM_NIVELES)
        self.post_message(self.ZoomCambiado(self.nivel))

    def action_colapsar(self) -> None:
        fila = self.filas[self.cursor] if self.filas else None
        if fila and fila.tiene_hijos:
            if fila.tarea.id in self.colapsados:
                self.colapsados.discard(fila.tarea.id)
            else:
                self.colapsados.add(fila.tarea.id)
            self._reconstruir()

    def action_alternar_estado(self) -> None:
        t = self.tarea_actual
        if t and not t.es_hito:
            self.post_message(self.AlternarEstado(t))

    def seleccionar_tarea(self, tarea_id: int) -> None:
        for i, f in enumerate(self.filas):
            if f.tarea.id == tarea_id:
                self.cursor = i
                return

    def _scroll_cursor_visible(self) -> None:
        visibles = max(self.size.height - HEADER_H, 1)
        top = int(self.scroll_offset.y)
        if self.cursor < top:
            self.scroll_to(y=self.cursor, animate=False)
        elif self.cursor > top + visibles - 1:
            self.scroll_to(y=self.cursor - visibles + 1, animate=False)


# -- Utilidades de segmentos -----------------------------------------------------

def _a_segmentos(celdas: list[tuple[str, Style]]) -> list[Segment]:
    if not celdas:
        return []
    segs: list[Segment] = []
    buf = [celdas[0][0]]
    est = celdas[0][1]
    for ch, st in celdas[1:]:
        if st == est:
            buf.append(ch)
        else:
            segs.append(Segment("".join(buf), est))
            buf = [ch]
            est = st
    segs.append(Segment("".join(buf), est))
    return segs


def _escribir(celdas: list[tuple[str, Style]], px: int, texto: str, estilo: Style) -> None:
    for i, ch in enumerate(texto):
        if 0 <= px + i < len(celdas):
            celdas[px + i] = (ch, estilo)
