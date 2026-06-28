"""Aplicación principal de Gproject."""

from __future__ import annotations

from textual.app import App

from gproject.config import db_path
from gproject.db import Database
from gproject.screens.main import MainScreen
from gproject.seed import poblar_demo


class GProjectApp(App):
    CSS_PATH = "styles/app.tcss"
    TITLE = "Gproject"
    SUB_TITLE = "Planificador de tareas · Gantt"

    def __init__(self, seed: bool = False) -> None:
        super().__init__()
        self._seed = seed
        self.db = Database(db_path())
        self.proyecto_activo_id: int | None = None

    def on_mount(self) -> None:
        self.theme = "tokyo-night"
        if self._seed:
            poblar_demo(self.db)
        proyectos = self.db.list_proyectos()
        if proyectos:
            self.proyecto_activo_id = proyectos[0].id
        self.push_screen(MainScreen())

    def on_unmount(self) -> None:
        self.db.close()
