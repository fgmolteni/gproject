"""Modal de búsqueda y filtros."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select


class FilterBar(ModalScreen[dict | None]):
    """Devuelve {'texto':str, 'estado':str|None, 'prioridad':str|None} o None."""

    def __init__(self, filtro: dict | None = None) -> None:
        super().__init__()
        self.filtro = filtro or {}

    def compose(self) -> ComposeResult:
        f = self.filtro
        with Vertical(id="dialogo", classes="modal modal-form"):
            yield Label("Buscar y filtrar", classes="titulo-modal")
            yield Label("Texto en el título")
            yield Input(value=f.get("texto", ""), placeholder="Buscar…", id="texto")
            with Horizontal(classes="fila-campos"):
                with Vertical(classes="campo"):
                    yield Label("Estado")
                    yield Select(
                        [("Pendiente", "todo"), ("En progreso", "doing"), ("Hecho", "done")],
                        value=f.get("estado") or Select.NULL,
                        prompt="— Cualquiera —", allow_blank=True, id="estado",
                    )
                with Vertical(classes="campo"):
                    yield Label("Prioridad")
                    yield Select(
                        [("Alta", "alta"), ("Media", "media"), ("Baja", "baja")],
                        value=f.get("prioridad") or Select.NULL,
                        prompt="— Cualquiera —", allow_blank=True, id="prioridad",
                    )
            with Horizontal(classes="botones"):
                yield Button("Aplicar", variant="success", id="aplicar")
                yield Button("Limpiar", id="limpiar")
                yield Button("Cancelar", id="cancelar")

    def on_mount(self) -> None:
        self.query_one("#texto", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancelar":
            self.dismiss(None)
        elif event.button.id == "limpiar":
            self.dismiss({"texto": "", "estado": None, "prioridad": None})
        else:
            estado = self.query_one("#estado", Select).value
            prioridad = self.query_one("#prioridad", Select).value
            self.dismiss(
                {
                    "texto": self.query_one("#texto", Input).value.strip(),
                    "estado": None if estado is Select.NULL else estado,
                    "prioridad": None if prioridad is Select.NULL else prioridad,
                }
            )

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
