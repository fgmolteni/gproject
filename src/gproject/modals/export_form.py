"""Modal para elegir el formato de exportación de las tareas."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select


class ExportModal(ModalScreen[dict | None]):
    """Devuelve {'formato': 'csv' | 'xlsx'} o None."""

    def compose(self) -> ComposeResult:
        with Vertical(id="dialogo", classes="modal modal-form"):
            yield Label("Exportar tareas", classes="titulo-modal")
            yield Label("Formato")
            yield Select(
                [("CSV (.csv)", "csv"), ("Excel (.xlsx)", "xlsx")],
                value="csv", allow_blank=False, id="formato",
            )
            with Horizontal(classes="botones"):
                yield Button("Exportar", variant="success", id="exportar")
                yield Button("Cancelar", id="cancelar")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancelar":
            self.dismiss(None)
            return
        self.dismiss({"formato": self.query_one("#formato", Select).value})

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
