"""Método de la ruta crítica (CPM) sobre el grafo de dependencias.

Calcula, en unidades de días y a partir de las duraciones y dependencias, el
inicio/fin temprano y tardío de cada tarea, su holgura y si pertenece a la ruta
crítica (holgura cero). Las fechas reales que fija el usuario se usan para dibujar;
el CPM sólo aporta el resaltado de la cadena que determina la duración del proyecto.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from gproject.models import Dependencia, Tarea


@dataclass
class ScheduleInfo:
    es: int  # inicio temprano (días desde t0)
    ef: int  # fin temprano
    ls: int  # inicio tardío
    lf: int  # fin tardío
    holgura: int
    critica: bool


def _orden_topologico(
    ids: set[int],
    preds: dict[int, list[int]],
    succs: dict[int, list[int]],
) -> list[int]:
    """Orden topológico (Kahn). Si hubiera ciclo, añade el resto al final."""
    indeg = {i: len(preds[i]) for i in ids}
    cola = [i for i in ids if indeg[i] == 0]
    orden: list[int] = []
    while cola:
        nodo = cola.pop()
        orden.append(nodo)
        for s in succs[nodo]:
            indeg[s] -= 1
            if indeg[s] == 0:
                cola.append(s)
    if len(orden) != len(ids):
        vistos = set(orden)
        orden.extend(i for i in ids if i not in vistos)
    return orden


def calcular_cpm(
    tareas: Iterable[Tarea],
    dependencias: Iterable[Dependencia],
) -> dict[int, ScheduleInfo]:
    """Devuelve un mapa ``tarea_id -> ScheduleInfo``."""
    dur = {t.id: t.duracion_efectiva for t in tareas}
    ids = set(dur)
    if not ids:
        return {}

    preds: dict[int, list[int]] = {i: [] for i in ids}
    succs: dict[int, list[int]] = {i: [] for i in ids}
    for d in dependencias:
        # «tarea_id depende de depende_de_id»: predecesor → sucesor
        if d.tarea_id in ids and d.depende_de_id in ids:
            preds[d.tarea_id].append(d.depende_de_id)
            succs[d.depende_de_id].append(d.tarea_id)

    orden = _orden_topologico(ids, preds, succs)

    # Pase hacia adelante
    es: dict[int, int] = {}
    ef: dict[int, int] = {}
    for i in orden:
        es[i] = max((ef[p] for p in preds[i]), default=0)
        ef[i] = es[i] + dur[i]

    proyecto_fin = max(ef.values(), default=0)

    # Pase hacia atrás
    lf: dict[int, int] = {}
    ls: dict[int, int] = {}
    for i in reversed(orden):
        lf[i] = min((ls[s] for s in succs[i]), default=proyecto_fin)
        ls[i] = lf[i] - dur[i]

    info: dict[int, ScheduleInfo] = {}
    for i in ids:
        holgura = ls[i] - es[i]
        info[i] = ScheduleInfo(es[i], ef[i], ls[i], lf[i], holgura, holgura == 0)
    return info
