"""Rutas y configuración de la aplicación."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_path

APP_NAME = "gproject"


def data_dir() -> Path:
    """Directorio de datos de la app (respeta XDG / GPROJECT_DATA_DIR)."""
    override = os.environ.get("GPROJECT_DATA_DIR")
    if override:
        path = Path(override).expanduser()
    else:
        path = user_data_path(APP_NAME)
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    """Ruta del archivo SQLite. Usa ``:memory:`` si GPROJECT_DB=memory."""
    env = os.environ.get("GPROJECT_DB")
    if env == "memory":
        return Path(":memory:")
    if env:
        return Path(env).expanduser()
    return data_dir() / "gproject.db"
