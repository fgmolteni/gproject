"""Modal para crear o editar un proyecto."""

from __future__ import annotations

from datetime import date

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from gproject.models import Proyecto, fecha_iso


class ProjectForm(ModalScreen[dict | None]):
    def __init__(self, proyecto: Proyecto | None = None) -> None:
        super().__init__()
        self.proyecto = proyecto

    def compose(self) -> ComposeResult:
        p = self.proyecto
        titulo = "Editar proyecto" if p else "Nuevo proyecto"
        with Vertical(id="dialogo", classes="modal modal-form"):
            yield Label(titulo, classes="titulo-modal")
            yield Label("Nombre")
            yield Input(value=p.nombre if p else "", placeholder="Nombre del proyecto",
                        id="nombre")
            yield Label("Descripción")
            yield Input(value=p.descripcion if p else "", placeholder="Opcional",
                        id="descripcion")
            yield Label("Fecha de inicio (YYYY-MM-DD)")
            yield Input(
                value=fecha_iso(p.fecha_inicio) if p and p.fecha_inicio else date.today().isoformat(),
                id="fecha_inicio",
            )
            with Horizontal(classes="botones"):
                yield Button("Guardar", variant="success", id="guardar")
                yield Button("Cancelar", id="cancelar")

    def on_mount(self) -> None:
        self.query_one("#nombre", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancelar":
            self.dismiss(None)
        else:
            self._guardar()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def _guardar(self) -> None:
        nombre = self.query_one("#nombre", Input).value.strip()
        if not nombre:
            self.query_one("#nombre", Input).focus()
            return
        fecha_txt = self.query_one("#fecha_inicio", Input).value.strip()
        try:
            fecha = date.fromisoformat(fecha_txt) if fecha_txt else None
        except ValueError:
            fecha = None
        self.dismiss(
            {
                "nombre": nombre,
                "descripcion": self.query_one("#descripcion", Input).value.strip(),
                "fecha_inicio": fecha,
            }
        )
