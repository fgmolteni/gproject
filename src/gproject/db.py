"""Capa de persistencia SQLite."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from gproject.models import (
    Dependencia,
    Etiqueta,
    Proyecto,
    Tarea,
    fecha_iso,
    parse_fecha,
)

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE proyectos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT NOT NULL,
    descripcion  TEXT NOT NULL DEFAULT '',
    color        TEXT NOT NULL DEFAULT '#4a9eff',
    fecha_inicio TEXT,
    fecha_fin    TEXT,
    archivado    INTEGER NOT NULL DEFAULT 0,
    creado_en    TEXT NOT NULL
);

CREATE TABLE tareas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    proyecto_id   INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    parent_id     INTEGER REFERENCES tareas(id) ON DELETE CASCADE,
    titulo        TEXT NOT NULL,
    descripcion   TEXT NOT NULL DEFAULT '',
    fecha_inicio  TEXT,
    duracion_dias INTEGER NOT NULL DEFAULT 1,
    progreso      INTEGER NOT NULL DEFAULT 0,
    estado        TEXT NOT NULL DEFAULT 'todo',
    prioridad     TEXT NOT NULL DEFAULT 'media',
    es_hito       INTEGER NOT NULL DEFAULT 0,
    orden         INTEGER NOT NULL DEFAULT 0,
    creado_en     TEXT NOT NULL,
    completado_en TEXT
);

CREATE TABLE etiquetas (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    color  TEXT NOT NULL DEFAULT '#8a8a8a'
);

CREATE TABLE tarea_etiquetas (
    tarea_id    INTEGER NOT NULL REFERENCES tareas(id) ON DELETE CASCADE,
    etiqueta_id INTEGER NOT NULL REFERENCES etiquetas(id) ON DELETE CASCADE,
    PRIMARY KEY (tarea_id, etiqueta_id)
);

CREATE TABLE dependencias (
    tarea_id      INTEGER NOT NULL REFERENCES tareas(id) ON DELETE CASCADE,
    depende_de_id INTEGER NOT NULL REFERENCES tareas(id) ON DELETE CASCADE,
    PRIMARY KEY (tarea_id, depende_de_id)
);

CREATE INDEX idx_tareas_proyecto ON tareas(proyecto_id);
CREATE INDEX idx_tareas_parent ON tareas(parent_id);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CycleError(ValueError):
    """Se intentó crear una dependencia que formaría un ciclo."""


class Database:
    """Envoltorio fino sobre ``sqlite3`` con el CRUD de la aplicación."""

    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    # -- Migraciones -------------------------------------------------------------

    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version < SCHEMA_VERSION:
            self.conn.executescript(SCHEMA)
            self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self.conn.commit()

    # -- Proyectos ---------------------------------------------------------------

    def list_proyectos(self, incluir_archivados: bool = False) -> list[Proyecto]:
        sql = "SELECT * FROM proyectos"
        if not incluir_archivados:
            sql += " WHERE archivado = 0"
        sql += " ORDER BY nombre COLLATE NOCASE"
        return [self._row_to_proyecto(r) for r in self.conn.execute(sql)]

    def get_proyecto(self, proyecto_id: int) -> Proyecto | None:
        row = self.conn.execute(
            "SELECT * FROM proyectos WHERE id = ?", (proyecto_id,)
        ).fetchone()
        return self._row_to_proyecto(row) if row else None

    def create_proyecto(
        self,
        nombre: str,
        descripcion: str = "",
        color: str = "#4a9eff",
        fecha_inicio: date | None = None,
        fecha_fin: date | None = None,
    ) -> int:
        cur = self.conn.execute(
            """INSERT INTO proyectos
               (nombre, descripcion, color, fecha_inicio, fecha_fin, creado_en)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                nombre,
                descripcion,
                color,
                fecha_iso(fecha_inicio),
                fecha_iso(fecha_fin),
                _now(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_proyecto(self, proyecto_id: int, **campos) -> None:
        self._update_row("proyectos", proyecto_id, campos)

    def delete_proyecto(self, proyecto_id: int) -> None:
        self.conn.execute("DELETE FROM proyectos WHERE id = ?", (proyecto_id,))
        self.conn.commit()

    # -- Tareas ------------------------------------------------------------------

    def list_tareas(self, proyecto_id: int) -> list[Tarea]:
        rows = self.conn.execute(
            "SELECT * FROM tareas WHERE proyecto_id = ? ORDER BY orden, id",
            (proyecto_id,),
        )
        tareas = [self._row_to_tarea(r) for r in rows]
        self._cargar_etiquetas(tareas)
        return tareas

    def get_tarea(self, tarea_id: int) -> Tarea | None:
        row = self.conn.execute(
            "SELECT * FROM tareas WHERE id = ?", (tarea_id,)
        ).fetchone()
        if not row:
            return None
        tarea = self._row_to_tarea(row)
        self._cargar_etiquetas([tarea])
        return tarea

    def create_tarea(
        self,
        proyecto_id: int,
        titulo: str,
        parent_id: int | None = None,
        descripcion: str = "",
        fecha_inicio: date | None = None,
        duracion_dias: int = 1,
        prioridad: str = "media",
        es_hito: bool = False,
        estado: str = "todo",
        progreso: int = 0,
        orden: int | None = None,
    ) -> int:
        if orden is None:
            orden = self._siguiente_orden(proyecto_id, parent_id)
        cur = self.conn.execute(
            """INSERT INTO tareas
               (proyecto_id, parent_id, titulo, descripcion, fecha_inicio,
                duracion_dias, progreso, estado, prioridad, es_hito, orden, creado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                proyecto_id,
                parent_id,
                titulo,
                descripcion,
                fecha_iso(fecha_inicio),
                duracion_dias,
                progreso,
                estado,
                prioridad,
                int(es_hito),
                orden,
                _now(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_tarea(self, tarea_id: int, **campos) -> None:
        if "fecha_inicio" in campos:
            campos["fecha_inicio"] = fecha_iso(campos["fecha_inicio"])
        if "es_hito" in campos:
            campos["es_hito"] = int(campos["es_hito"])
        # Mantener coherentes estado/progreso/completado_en
        if campos.get("estado") == "done":
            campos.setdefault("progreso", 100)
            campos.setdefault("completado_en", _now())
        elif "estado" in campos:
            campos.setdefault("completado_en", None)
        self._update_row("tareas", tarea_id, campos)

    def delete_tarea(self, tarea_id: int) -> None:
        # ON DELETE CASCADE limpia subtareas, etiquetas y dependencias
        self.conn.execute("DELETE FROM tareas WHERE id = ?", (tarea_id,))
        self.conn.commit()

    def _siguiente_orden(self, proyecto_id: int, parent_id: int | None) -> int:
        if parent_id is None:
            row = self.conn.execute(
                "SELECT COALESCE(MAX(orden), -1) + 1 FROM tareas "
                "WHERE proyecto_id = ? AND parent_id IS NULL",
                (proyecto_id,),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT COALESCE(MAX(orden), -1) + 1 FROM tareas WHERE parent_id = ?",
                (parent_id,),
            ).fetchone()
        return int(row[0])

    # -- Etiquetas ---------------------------------------------------------------

    def list_etiquetas(self) -> list[Etiqueta]:
        rows = self.conn.execute("SELECT * FROM etiquetas ORDER BY nombre")
        return [Etiqueta(r["id"], r["nombre"], r["color"]) for r in rows]

    def get_or_create_etiqueta(self, nombre: str, color: str = "#8a8a8a") -> int:
        row = self.conn.execute(
            "SELECT id FROM etiquetas WHERE nombre = ?", (nombre,)
        ).fetchone()
        if row:
            return int(row["id"])
        cur = self.conn.execute(
            "INSERT INTO etiquetas (nombre, color) VALUES (?, ?)", (nombre, color)
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def set_tarea_etiquetas(self, tarea_id: int, etiqueta_ids: list[int]) -> None:
        self.conn.execute(
            "DELETE FROM tarea_etiquetas WHERE tarea_id = ?", (tarea_id,)
        )
        self.conn.executemany(
            "INSERT INTO tarea_etiquetas (tarea_id, etiqueta_id) VALUES (?, ?)",
            [(tarea_id, eid) for eid in etiqueta_ids],
        )
        self.conn.commit()

    def _cargar_etiquetas(self, tareas: list[Tarea]) -> None:
        if not tareas:
            return
        by_id = {t.id: t for t in tareas}
        marcas = ",".join("?" * len(by_id))
        rows = self.conn.execute(
            f"""SELECT te.tarea_id, e.id, e.nombre, e.color
                FROM tarea_etiquetas te JOIN etiquetas e ON e.id = te.etiqueta_id
                WHERE te.tarea_id IN ({marcas})""",
            tuple(by_id),
        )
        for r in rows:
            by_id[r["tarea_id"]].etiquetas.append(
                Etiqueta(r["id"], r["nombre"], r["color"])
            )

    # -- Dependencias ------------------------------------------------------------

    def list_dependencias(self, proyecto_id: int) -> list[Dependencia]:
        rows = self.conn.execute(
            """SELECT d.tarea_id, d.depende_de_id
               FROM dependencias d JOIN tareas t ON t.id = d.tarea_id
               WHERE t.proyecto_id = ?""",
            (proyecto_id,),
        )
        return [Dependencia(r["tarea_id"], r["depende_de_id"]) for r in rows]

    def add_dependencia(self, tarea_id: int, depende_de_id: int) -> None:
        """Añade «tarea_id depende de depende_de_id». Lanza ``CycleError``."""
        if tarea_id == depende_de_id:
            raise CycleError("Una tarea no puede depender de sí misma.")
        if self._crearia_ciclo(tarea_id, depende_de_id):
            raise CycleError("La dependencia formaría un ciclo.")
        self.conn.execute(
            "INSERT OR IGNORE INTO dependencias (tarea_id, depende_de_id) VALUES (?, ?)",
            (tarea_id, depende_de_id),
        )
        self.conn.commit()

    def remove_dependencia(self, tarea_id: int, depende_de_id: int) -> None:
        self.conn.execute(
            "DELETE FROM dependencias WHERE tarea_id = ? AND depende_de_id = ?",
            (tarea_id, depende_de_id),
        )
        self.conn.commit()

    def _crearia_ciclo(self, tarea_id: int, depende_de_id: int) -> bool:
        """¿Añadir la arista predecesor→sucesor crea un ciclo?

        Arista lógica: ``depende_de_id`` (predecesor) → ``tarea_id`` (sucesor).
        Hay ciclo si ``depende_de_id`` ya es alcanzable como sucesor de ``tarea_id``.
        """
        # sucesores[x] = tareas que dependen de x
        adj: dict[int, list[int]] = {}
        for r in self.conn.execute(
            "SELECT tarea_id, depende_de_id FROM dependencias"
        ):
            adj.setdefault(r["depende_de_id"], []).append(r["tarea_id"])

        objetivo = depende_de_id
        pila = [tarea_id]
        visto = set()
        while pila:
            nodo = pila.pop()
            if nodo == objetivo:
                return True
            if nodo in visto:
                continue
            visto.add(nodo)
            pila.extend(adj.get(nodo, ()))
        return False

    # -- Utilidades internas -----------------------------------------------------

    def _update_row(self, tabla: str, row_id: int, campos: dict) -> None:
        if not campos:
            return
        asignaciones = ", ".join(f"{k} = ?" for k in campos)
        valores = list(campos.values()) + [row_id]
        self.conn.execute(
            f"UPDATE {tabla} SET {asignaciones} WHERE id = ?", valores
        )
        self.conn.commit()

    @staticmethod
    def _row_to_proyecto(row: sqlite3.Row) -> Proyecto:
        return Proyecto(
            id=row["id"],
            nombre=row["nombre"],
            descripcion=row["descripcion"] or "",
            color=row["color"],
            fecha_inicio=parse_fecha(row["fecha_inicio"]),
            fecha_fin=parse_fecha(row["fecha_fin"]),
            archivado=bool(row["archivado"]),
            creado_en=row["creado_en"] or "",
        )

    @staticmethod
    def _row_to_tarea(row: sqlite3.Row) -> Tarea:
        return Tarea(
            id=row["id"],
            proyecto_id=row["proyecto_id"],
            parent_id=row["parent_id"],
            titulo=row["titulo"],
            descripcion=row["descripcion"] or "",
            fecha_inicio=parse_fecha(row["fecha_inicio"]),
            duracion_dias=row["duracion_dias"],
            progreso=row["progreso"],
            estado=row["estado"],
            prioridad=row["prioridad"],
            es_hito=bool(row["es_hito"]),
            orden=row["orden"],
            creado_en=row["creado_en"] or "",
            completado_en=row["completado_en"],
        )
