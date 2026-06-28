"""Pruebas del cálculo de la ruta crítica (CPM)."""

from __future__ import annotations

from gproject.models import Dependencia, Tarea
from gproject.scheduling import calcular_cpm


def _tarea(tid: int, dur: int) -> Tarea:
    return Tarea(id=tid, proyecto_id=1, titulo=f"T{tid}", duracion_dias=dur)


def test_cpm_grafo_conocido():
    # A(2) -> B(3) \
    #            -> D(4)
    # A(2) -> C(2) /
    a, b, c, d = _tarea(1, 2), _tarea(2, 3), _tarea(3, 2), _tarea(4, 4)
    deps = [
        Dependencia(b.id, a.id),
        Dependencia(c.id, a.id),
        Dependencia(d.id, b.id),
        Dependencia(d.id, c.id),
    ]
    info = calcular_cpm([a, b, c, d], deps)

    assert info[a.id].es == 0 and info[a.id].ef == 2
    assert info[b.id].es == 2 and info[b.id].ef == 5
    assert info[d.id].es == 5 and info[d.id].ef == 9

    # C tiene 1 día de holgura; el resto es ruta crítica
    assert info[c.id].holgura == 1
    assert not info[c.id].critica
    assert info[a.id].critica
    assert info[b.id].critica
    assert info[d.id].critica


def test_cpm_vacio():
    assert calcular_cpm([], []) == {}


def test_cpm_sin_dependencias():
    a, b = _tarea(1, 3), _tarea(2, 5)
    info = calcular_cpm([a, b], [])
    # La tarea más larga determina la duración del proyecto (holgura 0)
    assert info[b.id].holgura == 0
    assert info[a.id].holgura == 2
