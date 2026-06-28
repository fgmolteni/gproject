"""Punto de entrada de la línea de comandos."""

from __future__ import annotations

import argparse

from gproject.app import GProjectApp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gproject",
        description="TUI planificadora de tareas con diagrama de Gantt.",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Cargar datos de ejemplo si la base está vacía.",
    )
    args = parser.parse_args()

    app = GProjectApp(seed=args.seed)
    app.run()


if __name__ == "__main__":
    main()
