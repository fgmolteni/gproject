"""Modal para gestionar las dependencias de una tarea."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select

from gproject.models import Dependencia, Tarea


class DependencyModal(ModalScreen[dict | None]):
    """Devuelve {'add': id} | {'remove': id} | None."""

    def __init__(self, tarea: Tarea, tareas: list[Tarea],
                 dependencias: list[Dependencia]) -> None:
        super().__init__()
        self.tarea = tarea
        self.tareas = tareas
        self.dependencias = dependencias

    def compose(self) -> ComposeResult:
        by_id = {t.id: t for t in self.tareas}
        actuales = [d.depende_de_id for d in self.dependencias if d.tarea_id == self.tarea.id]
        candidatos = [
            (t.titulo, t.id)
            for t in self.tareas
            if t.id != self.tarea.id and t.id not in actuales
        ]
        with Vertical(id="dialogo", classes="modal modal-form"):
            yield Label(f"Dependencias de: {self.tarea.titulo}", classes="titulo-modal")
            yield Label("Esta tarea depende de:", classes="subtitulo")
            with VerticalScroll(id="lista-deps"):
                if not actuales:
                    yield Label("  (ninguna)", classes="vacio")
                for pred_id in actuales:
                    nombre = by_id[pred_id].titulo if pred_id in by_id else f"#{pred_id}"
                    with Horizontal(classes="fila-dep"):
                        yield Label(f"  • {nombre}", classes="dep-nombre")
                        yield Button("Quitar", variant="error", id=f"rm-{pred_id}")
            yield Label("Añadir dependencia", classes="subtitulo")
            with Horizontal(classes="fila-campos"):
                yield Select(candidatos, prompt="Elegir tarea…", id="nueva",
                             allow_blank=True)
                yield Button("Añadir", variant="success", id="add")
            with Horizontal(classes="botones"):
                yield Button("Cerrar", id="cerrar")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "cerrar":
            self.dismiss(None)
        elif bid == "add":
            val = self.query_one("#nueva", Select).value
            if val is Select.NULL:
                return
            self.dismiss({"add": int(val)})
        elif bid.startswith("rm-"):
            self.dismiss({"remove": int(bid[3:])})

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
