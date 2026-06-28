"""Modal para elegir el proyecto activo."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from gproject.models import Proyecto


class ProjectPicker(ModalScreen[int | None]):
    def __init__(self, proyectos: list[Proyecto], activo_id: int | None = None) -> None:
        super().__init__()
        self.proyectos = proyectos
        self.activo_id = activo_id

    def compose(self) -> ComposeResult:
        with Vertical(id="dialogo", classes="modal"):
            yield Label("Elegir proyecto", classes="titulo-modal")
            opciones = [Option(p.nombre, id=str(p.id)) for p in self.proyectos]
            yield OptionList(*opciones, id="proyectos")

    def on_mount(self) -> None:
        ol = self.query_one(OptionList)
        ol.focus()
        if self.activo_id is not None:
            for i, p in enumerate(self.proyectos):
                if p.id == self.activo_id:
                    ol.highlighted = i
                    break

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(int(event.option.id))

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
