"""Pantalla principal: barra de info + vista central + detalle."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, Header, Static

from gproject.db import CycleError
from gproject.models import PRIORIDAD_COLOR, Tarea
from gproject.modals.confirm import ConfirmModal
from gproject.modals.dependency import DependencyModal
from gproject.modals.filter_bar import FilterBar
from gproject.modals.project_form import ProjectForm
from gproject.modals.project_picker import ProjectPicker
from gproject.modals.task_form import TaskForm
from gproject.scheduling import calcular_cpm
from gproject.widgets.gantt_chart import GanttView
from gproject.widgets.kanban_board import KanbanView

CICLO_ESTADO = {"todo": "doing", "doing": "done", "done": "todo"}

AYUDA = """[b]Navegación[/b]
  ↑/↓ (k/j)   mover cursor
  ←/→         desplazar tiempo / cambiar columna
  +/-         zoom (Día / Semana / Mes)
  c           colapsar/expandir fase
  espacio     cambiar estado de la tarea

[b]Acciones[/b]
  n  nueva tarea        N  nuevo proyecto
  e  editar             d  borrar
  D  dependencias       M  marcar/quitar hito
  v  Gantt/Kanban       /  buscar/filtrar
  p  cambiar proyecto
  ?  ayuda              q  salir

[b]Leyenda[/b]
  █ progreso   ░ pendiente   ◆ hito
  [#ff5c57]rojo[/] = ruta crítica   [#e0af68]┊[/] = hoy
"""


class HelpModal(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        yield Static(Text.from_markup(AYUDA), id="ayuda", classes="modal")

    def on_key(self, event) -> None:
        self.dismiss(None)


class MainScreen(Screen):
    BINDINGS = [
        Binding("n", "nueva_tarea", "Nueva"),
        Binding("N", "nuevo_proyecto", "Proyecto"),
        Binding("e", "editar", "Editar"),
        Binding("d", "borrar", "Borrar"),
        Binding("D", "dependencias", "Deps"),
        Binding("M", "hito", "Hito"),
        Binding("v", "alternar_vista", "Vista"),
        Binding("slash", "filtrar", "Filtrar"),
        Binding("p", "cambiar_proyecto", "Proyecto activo"),
        Binding("question_mark", "ayuda", "Ayuda"),
        Binding("q", "salir", "Salir"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.filtro: dict = {}
        self.vista = "gantt"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="barra")
        gantt = GanttView()
        gantt.id = "gantt"
        yield gantt
        kanban = KanbanView()
        kanban.id = "kanban"
        yield kanban
        yield Static(id="detalle")
        yield Footer()

    @property
    def db(self):
        return self.app.db

    @property
    def gantt(self) -> GanttView:
        return self.query_one(GanttView)

    @property
    def kanban(self) -> KanbanView:
        return self.query_one(KanbanView)

    @property
    def vista_activa(self):
        return self.kanban if self.vista == "kanban" else self.gantt

    @property
    def tarea_actual(self) -> Tarea | None:
        return self.vista_activa.tarea_actual

    def _pid(self) -> int | None:
        return self.app.proyecto_activo_id

    def on_mount(self) -> None:
        self._mostrar_vista()
        self._recargar()

    def _mostrar_vista(self) -> None:
        self.gantt.display = self.vista == "gantt"
        self.kanban.display = self.vista == "kanban"
        self.vista_activa.focus()

    # -- Carga -------------------------------------------------------------------

    def _aplicar_filtro(self, tareas: list[Tarea]) -> list[Tarea]:
        f = self.filtro
        if not (f.get("texto") or f.get("estado") or f.get("prioridad")):
            return tareas
        texto = (f.get("texto") or "").lower()

        def coincide(t: Tarea) -> bool:
            if texto and texto not in t.titulo.lower():
                return False
            if f.get("estado") and t.estado != f["estado"]:
                return False
            if f.get("prioridad") and t.prioridad != f["prioridad"]:
                return False
            return True

        por_id = {t.id: t for t in tareas}
        visibles: set[int] = set()
        for t in tareas:
            if coincide(t):
                visibles.add(t.id)
                padre = t.parent_id
                while padre is not None and padre in por_id and padre not in visibles:
                    visibles.add(padre)
                    padre = por_id[padre].parent_id
        return [t for t in tareas if t.id in visibles]

    def _recargar(self, preservar_id: int | None = None) -> None:
        pid = self._pid()
        if pid is None:
            self.gantt.cargar([], [])
            self.kanban.cargar([])
            self.query_one("#barra", Static).update(
                Text("  Sin proyectos. Pulsa  N  para crear uno.", style="#e0af68")
            )
            self.query_one("#detalle", Static).update("")
            return
        proyecto = self.db.get_proyecto(pid)
        tareas = self.db.list_tareas(pid)
        deps = self.db.list_dependencias(pid)
        tareas_filtradas = self._aplicar_filtro(tareas)
        self.gantt.cargar(tareas_filtradas, deps)
        self.kanban.cargar(tareas_filtradas)
        if preservar_id is not None:
            self.gantt.seleccionar_tarea(preservar_id)
            self.kanban.seleccionar_tarea(preservar_id)
        self._actualizar_barra(proyecto, tareas)
        self._actualizar_detalle(self.tarea_actual)
        self.vista_activa.focus()

    def _actualizar_barra(self, proyecto, tareas: list[Tarea]) -> None:
        hechas = sum(1 for t in tareas if t.estado == "done")
        total = len(tareas)
        filtro_txt = "  ·  [filtro activo]" if self.filtro.get("texto") or \
            self.filtro.get("estado") or self.filtro.get("prioridad") else ""
        t = Text()
        t.append(f"  {proyecto.nombre}  ", style="bold #7aa2f7")
        t.append(f"· {hechas}/{total} hechas ", style="#9aa5ce")
        t.append(f"· vista: {self.vista.capitalize()} ", style="#9aa5ce")
        if self.vista == "gantt":
            t.append(f"· zoom: {self.gantt.nivel_zoom_label} ", style="#9aa5ce")
        t.append(filtro_txt, style="#e0af68")
        self.query_one("#barra", Static).update(t)

    def _actualizar_detalle(self, tarea: Tarea | None) -> None:
        det = self.query_one("#detalle", Static)
        if tarea is None:
            det.update("")
            return
        info = calcular_cpm(self.db.list_tareas(self._pid()),
                            self.db.list_dependencias(self._pid())).get(tarea.id)
        t = Text()
        t.append(f"  {tarea.icono} {tarea.titulo}", style="bold")
        if tarea.fecha_inicio:
            t.append(f"  ·  {tarea.fecha_inicio.isoformat()}", style="#9aa5ce")
            if not tarea.es_hito and tarea.fecha_fin:
                t.append(f" → {tarea.fecha_fin.isoformat()} ({tarea.duracion_dias}d)",
                         style="#9aa5ce")
        t.append("  ·  ", style="#565f89")
        t.append(tarea.prioridad, style=PRIORIDAD_COLOR.get(tarea.prioridad, "#9aa5ce"))
        if not tarea.es_hito:
            t.append(f"  ·  {tarea.progreso}%", style="#9aa5ce")
        if info and info.critica:
            t.append("  ·  RUTA CRÍTICA", style="bold #ff5c57")
        elif info:
            t.append(f"  ·  holgura {info.holgura}d", style="#565f89")
        if tarea.etiquetas:
            t.append("  ·  ", style="#565f89")
            for e in tarea.etiquetas:
                t.append(f"#{e.nombre} ", style=e.color)
        det.update(t)

    # -- Mensajes del widget -----------------------------------------------------

    def on_gantt_view_tarea_resaltada(self, message: GanttView.TareaResaltada) -> None:
        if self.vista == "gantt":
            self._actualizar_detalle(message.tarea)

    def on_gantt_view_alternar_estado(self, message: GanttView.AlternarEstado) -> None:
        if self.vista == "gantt":
            self._alternar_estado(message.tarea)

    def on_kanban_view_tarea_resaltada(self, message: KanbanView.TareaResaltada) -> None:
        if self.vista == "kanban":
            self._actualizar_detalle(message.tarea)

    def on_kanban_view_alternar_estado(self, message: KanbanView.AlternarEstado) -> None:
        if self.vista == "kanban":
            self._alternar_estado(message.tarea)

    def _alternar_estado(self, tarea: Tarea) -> None:
        nuevo = CICLO_ESTADO.get(tarea.estado, "todo")
        self.db.update_tarea(tarea.id, estado=nuevo)
        self._recargar(preservar_id=tarea.id)

    # -- Etiquetas ---------------------------------------------------------------

    def _set_etiquetas(self, tarea_id: int, nombres: list[str]) -> None:
        ids = [self.db.get_or_create_etiqueta(n) for n in nombres]
        self.db.set_tarea_etiquetas(tarea_id, ids)

    # -- Acciones: tareas --------------------------------------------------------

    def action_nueva_tarea(self) -> None:
        if self._pid() is None:
            self.notify("Crea un proyecto primero (N).", severity="warning")
            return
        tareas = self.db.list_tareas(self._pid())
        actual = self.tarea_actual
        sugerido = None
        if actual:
            sugerido = actual.id if not actual.es_hito and \
                any(x.parent_id == actual.id for x in tareas) else actual.parent_id
        self.app.push_screen(TaskForm(tareas, None, sugerido), self._crear_tarea)

    def _crear_tarea(self, datos: dict | None) -> None:
        if not datos:
            return
        etqs = datos.pop("etiquetas")
        tid = self.db.create_tarea(self._pid(), **datos)
        self._set_etiquetas(tid, etqs)
        self._recargar(preservar_id=tid)

    def action_editar(self) -> None:
        t = self.tarea_actual
        if not t:
            return
        tareas = self.db.list_tareas(self._pid())
        self.app.push_screen(TaskForm(tareas, t), lambda d: self._editar_tarea(t.id, d))

    def _editar_tarea(self, tarea_id: int, datos: dict | None) -> None:
        if not datos:
            return
        etqs = datos.pop("etiquetas")
        self.db.update_tarea(tarea_id, **datos)
        self._set_etiquetas(tarea_id, etqs)
        self._recargar(preservar_id=tarea_id)

    def action_borrar(self) -> None:
        t = self.tarea_actual
        if not t:
            return

        def confirmar(ok: bool | None) -> None:
            if ok:
                self.db.delete_tarea(t.id)
                self._recargar()

        self.app.push_screen(
            ConfirmModal(f"¿Borrar «{t.titulo}» y sus subtareas?"), confirmar
        )

    def action_hito(self) -> None:
        t = self.tarea_actual
        if not t:
            return
        self.db.update_tarea(t.id, es_hito=not t.es_hito)
        self._recargar(preservar_id=t.id)

    def action_dependencias(self) -> None:
        t = self.tarea_actual
        if not t:
            return
        self._abrir_dependencias(t.id)

    def _abrir_dependencias(self, tarea_id: int) -> None:
        tarea = self.db.get_tarea(tarea_id)
        if tarea is None:
            return
        tareas = self.db.list_tareas(self._pid())
        deps = self.db.list_dependencias(self._pid())

        def manejar(resultado: dict | None) -> None:
            if not resultado:
                self._recargar(preservar_id=tarea_id)
                return
            if "add" in resultado:
                try:
                    self.db.add_dependencia(tarea_id, resultado["add"])
                except CycleError as e:
                    self.notify(str(e), severity="error")
            elif "remove" in resultado:
                self.db.remove_dependencia(tarea_id, resultado["remove"])
            self._abrir_dependencias(tarea_id)

        self.app.push_screen(DependencyModal(tarea, tareas, deps), manejar)

    # -- Acciones: proyectos / filtros / ayuda -----------------------------------

    def action_alternar_vista(self) -> None:
        actual = self.tarea_actual
        self.vista = "kanban" if self.vista == "gantt" else "gantt"
        self._mostrar_vista()
        self._recargar(preservar_id=actual.id if actual else None)

    def action_nuevo_proyecto(self) -> None:
        self.app.push_screen(ProjectForm(), self._crear_proyecto)

    def _crear_proyecto(self, datos: dict | None) -> None:
        if not datos:
            return
        pid = self.db.create_proyecto(**datos)
        self.app.proyecto_activo_id = pid
        self.filtro = {}
        self._recargar()

    def action_cambiar_proyecto(self) -> None:
        proyectos = self.db.list_proyectos()
        if not proyectos:
            self.notify("No hay proyectos. Crea uno con N.", severity="warning")
            return

        def elegir(pid: int | None) -> None:
            if pid is not None:
                self.app.proyecto_activo_id = pid
                self.filtro = {}
                self._recargar()

        self.app.push_screen(ProjectPicker(proyectos, self._pid()), elegir)

    def action_filtrar(self) -> None:
        def aplicar(f: dict | None) -> None:
            if f is not None:
                self.filtro = f
                self._recargar()

        self.app.push_screen(FilterBar(self.filtro), aplicar)

    def action_ayuda(self) -> None:
        self.app.push_screen(HelpModal())

    def action_salir(self) -> None:
        self.app.exit()
