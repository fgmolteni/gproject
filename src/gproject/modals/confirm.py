"""Modal de confirmación Sí/No."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmModal(ModalScreen[bool]):
    def __init__(self, mensaje: str) -> None:
        super().__init__()
        self.mensaje = mensaje

    def compose(self) -> ComposeResult:
        with Vertical(id="dialogo", classes="modal"):
            yield Label(self.mensaje, id="mensaje")
            with Horizontal(classes="botones"):
                yield Button("Sí, borrar", variant="error", id="si")
                yield Button("Cancelar", variant="primary", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "si")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)
