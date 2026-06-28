"""Pruebas de la capa de datos."""

from __future__ import annotations

from datetime import date

import pytest

from gproject.db import CycleError, Database


@pytest.fixture
def db() -> Database:
    base = Database(":memory:")
    yield base
    base.close()


def test_crear_y_listar_proyecto(db: Database):
    pid = db.create_proyecto("Demo", "desc", fecha_inicio=date(2026, 1, 1))
    proyectos = db.list_proyectos()
    assert len(proyectos) == 1
    assert proyectos[0].nombre == "Demo"
    assert proyectos[0].fecha_inicio == date(2026, 1, 1)


def test_crear_tareas_y_subtareas_ordenadas(db: Database):
    pid = db.create_proyecto("P")
    a = db.create_tarea(pid, "A")
    b = db.create_tarea(pid, "B")
    hijo = db.create_tarea(pid, "A.1", parent_id=a)
    tareas = db.list_tareas(pid)
    # lista plana ordenada por (orden, id); la jerarquía la arma el widget
    assert {t.titulo for t in tareas} == {"A", "B", "A.1"}
    assert next(t for t in tareas if t.id == hijo).parent_id == a


def test_etiquetas_n_a_n(db: Database):
    pid = db.create_proyecto("P")
    tid = db.create_tarea(pid, "T")
    e1 = db.get_or_create_etiqueta("frontend")
    e2 = db.get_or_create_etiqueta("urgente")
    assert db.get_or_create_etiqueta("frontend") == e1  # idempotente
    db.set_tarea_etiquetas(tid, [e1, e2])
    tarea = db.get_tarea(tid)
    assert {e.nombre for e in tarea.etiquetas} == {"frontend", "urgente"}


def test_estado_done_marca_progreso_y_completado(db: Database):
    pid = db.create_proyecto("P")
    tid = db.create_tarea(pid, "T", progreso=10)
    db.update_tarea(tid, estado="done")
    t = db.get_tarea(tid)
    assert t.estado == "done"
    assert t.progreso == 100
    assert t.completado_en is not None


def test_dependencia_y_anticiclo(db: Database):
    pid = db.create_proyecto("P")
    a = db.create_tarea(pid, "A")
    b = db.create_tarea(pid, "B")
    c = db.create_tarea(pid, "C")
    db.add_dependencia(b, a)  # B depende de A
    db.add_dependencia(c, b)  # C depende de B
    assert len(db.list_dependencias(pid)) == 2
    with pytest.raises(CycleError):
        db.add_dependencia(a, c)  # crearía A->B->C->A
    with pytest.raises(CycleError):
        db.add_dependencia(a, a)  # autodependencia


def test_borrado_en_cascada(db: Database):
    pid = db.create_proyecto("P")
    a = db.create_tarea(pid, "A")
    hijo = db.create_tarea(pid, "A.1", parent_id=a)
    b = db.create_tarea(pid, "B")
    db.add_dependencia(b, a)
    db.delete_tarea(a)
    titulos = [t.titulo for t in db.list_tareas(pid)]
    assert titulos == ["B"]  # subtarea eliminada en cascada
    assert db.list_dependencias(pid) == []  # dependencia eliminada
