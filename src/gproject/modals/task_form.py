"""Modal para crear o editar una tarea."""

from __future__ import annotations

from datetime import date

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select

from gproject.models import ESTADOS, PRIORIDADES, Tarea, fecha_iso


class TaskForm(ModalScreen[dict | None]):
    def __init__(
        self,
        tareas: list[Tarea],
        tarea: Tarea | None = None,
        parent_id_sugerido: int | None = None,
    ) -> None:
        super().__init__()
        self.tareas = tareas
        self.tarea = tarea
        self.parent_id_sugerido = parent_id_sugerido

    def _ids_prohibidos(self) -> set[int]:
        """Una tarea no puede ser su propio padre ni el de sus descendientes."""
        if not self.tarea:
            return set()
        prohibidos = {self.tarea.id}
        cambio = True
        while cambio:
            cambio = False
            for t in self.tareas:
                if t.parent_id in prohibidos and t.id not in prohibidos:
                    prohibidos.add(t.id)
                    cambio = True
        return prohibidos

    def compose(self) -> ComposeResult:
        t = self.tarea
        titulo = "Editar tarea" if t else "Nueva tarea"
        prohibidos = self._ids_prohibidos()
        opciones_padre = [
            (("  " * 0) + p.titulo, p.id)
            for p in self.tareas
            if p.id not in prohibidos and not p.es_hito
        ]
        parent_default = (t.parent_id if t else self.parent_id_sugerido)

        with Vertical(id="dialogo", classes="modal modal-form"):
            yield Label(titulo, classes="titulo-modal")
            yield Label("Título")
            yield Input(value=t.titulo if t else "", placeholder="Título de la tarea",
                        id="titulo")

            with Horizontal(classes="fila-campos"):
                with Vertical(classes="campo"):
                    yield Label("Inicio (YYYY-MM-DD)")
                    yield Input(
                        value=fecha_iso(t.fecha_inicio) if t and t.fecha_inicio
                        else date.today().isoformat(),
                        id="fecha_inicio",
                    )
                with Vertical(classes="campo"):
                    yield Label("Duración (días)")
                    yield Input(value=str(t.duracion_dias) if t else "1",
                                id="duracion", type="integer")

            with Horizontal(classes="fila-campos"):
                with Vertical(classes="campo"):
                    yield Label("Prioridad")
                    yield Select(
                        [(p.capitalize(), p) for p in PRIORIDADES],
                        value=t.prioridad if t else "media",
                        allow_blank=False, id="prioridad",
                    )
                with Vertical(classes="campo"):
                    yield Label("Estado")
                    yield Select(
                        [("Pendiente", "todo"), ("En progreso", "doing"), ("Hecho", "done")],
                        value=t.estado if t else "todo",
                        allow_blank=False, id="estado",
                    )

            with Horizontal(classes="fila-campos"):
                with Vertical(classes="campo"):
                    yield Label("Progreso (%)")
                    yield Input(value=str(t.progreso) if t else "0",
                                id="progreso", type="integer")
                with Vertical(classes="campo"):
                    yield Label("Padre / fase")
                    yield Select(opciones_padre, value=parent_default or Select.NULL,
                                 allow_blank=True, prompt="— Ninguno —", id="parent")

            yield Checkbox("Es un hito (◆)", value=t.es_hito if t else False, id="es_hito")
            etqs = ", ".join(e.nombre for e in t.etiquetas) if t else ""
            yield Label("Etiquetas (separadas por coma)")
            yield Input(value=etqs, placeholder="frontend, urgente", id="etiquetas")

            with Horizontal(classes="botones"):
                yield Button("Guardar", variant="success", id="guardar")
                yield Button("Cancelar", id="cancelar")

    def on_mount(self) -> None:
        self.query_one("#titulo", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancelar":
            self.dismiss(None)
        else:
            self._guardar()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def _entero(self, id_: str, defecto: int = 0) -> int:
        try:
            return int(self.query_one(f"#{id_}", Input).value or defecto)
        except ValueError:
            return defecto

    def _guardar(self) -> None:
        titulo = self.query_one("#titulo", Input).value.strip()
        if not titulo:
            self.query_one("#titulo", Input).focus()
            return
        try:
            fecha = date.fromisoformat(self.query_one("#fecha_inicio", Input).value.strip())
        except ValueError:
            fecha = None

        parent_val = self.query_one("#parent", Select).value
        parent_id = None if parent_val is Select.NULL else int(parent_val)
        etqs = [
            e.strip()
            for e in self.query_one("#etiquetas", Input).value.split(",")
            if e.strip()
        ]
        self.dismiss(
            {
                "titulo": titulo,
                "fecha_inicio": fecha,
                "duracion_dias": max(self._entero("duracion", 1), 0),
                "prioridad": self.query_one("#prioridad", Select).value,
                "estado": self.query_one("#estado", Select).value,
                "progreso": max(0, min(self._entero("progreso", 0), 100)),
                "parent_id": parent_id,
                "es_hito": self.query_one("#es_hito", Checkbox).value,
                "etiquetas": etqs,
            }
        )
