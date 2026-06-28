"""Datos de ejemplo para probar la aplicación de inmediato."""

from __future__ import annotations

from datetime import date, timedelta

from gproject.db import Database


def poblar_demo(db: Database) -> int | None:
    """Crea un proyecto demo si no hay proyectos. Devuelve su id (o None)."""
    if db.list_proyectos(incluir_archivados=True):
        return None

    base = date.today() - timedelta(days=10)

    def f(offset: int) -> date:
        return base + timedelta(days=offset)

    pid = db.create_proyecto(
        nombre="Sitio Web v1",
        descripcion="Rediseño y lanzamiento del sitio corporativo.",
        color="#4a9eff",
        fecha_inicio=f(0),
        fecha_fin=f(26),
    )

    et_dis = db.get_or_create_etiqueta("diseño", "#b48ead")
    et_back = db.get_or_create_etiqueta("backend", "#5e81ac")
    et_front = db.get_or_create_etiqueta("frontend", "#88c0d0")
    et_urg = db.get_or_create_etiqueta("urgente", "#bf616a")

    # Fases (tareas padre con barra resumen)
    fase_dis = db.create_tarea(pid, "Diseño", fecha_inicio=f(0), duracion_dias=10,
                               prioridad="alta", estado="doing", progreso=80)
    fase_dev = db.create_tarea(pid, "Desarrollo", fecha_inicio=f(10), duracion_dias=11,
                               prioridad="alta", estado="doing", progreso=25)
    fase_lan = db.create_tarea(pid, "Lanzamiento", fecha_inicio=f(21), duracion_dias=5,
                               prioridad="media", estado="todo", progreso=0)

    # Tareas de Diseño
    t_inv = db.create_tarea(pid, "Investigación", parent_id=fase_dis,
                            fecha_inicio=f(0), duracion_dias=3,
                            prioridad="media", estado="done", progreso=100)
    t_wir = db.create_tarea(pid, "Wireframes", parent_id=fase_dis,
                            fecha_inicio=f(3), duracion_dias=4,
                            prioridad="alta", estado="done", progreso=100)
    t_kit = db.create_tarea(pid, "UI Kit", parent_id=fase_dis,
                            fecha_inicio=f(7), duracion_dias=3,
                            prioridad="alta", estado="doing", progreso=60)

    # Tareas de Desarrollo
    t_api = db.create_tarea(pid, "Backend API", parent_id=fase_dev,
                            fecha_inicio=f(10), duracion_dias=8,
                            prioridad="alta", estado="doing", progreso=40)
    t_fro = db.create_tarea(pid, "Frontend", parent_id=fase_dev,
                            fecha_inicio=f(10), duracion_dias=7,
                            prioridad="media", estado="todo", progreso=10)
    t_int = db.create_tarea(pid, "Integración", parent_id=fase_dev,
                            fecha_inicio=f(18), duracion_dias=3,
                            prioridad="alta", estado="todo", progreso=0)

    # Tareas de Lanzamiento
    t_pru = db.create_tarea(pid, "Pruebas", parent_id=fase_lan,
                            fecha_inicio=f(21), duracion_dias=4,
                            prioridad="alta", estado="todo", progreso=0)
    t_ent = db.create_tarea(pid, "Entrega v1", parent_id=fase_lan,
                            fecha_inicio=f(25), duracion_dias=0,
                            es_hito=True, prioridad="alta", estado="todo")

    # Etiquetas
    db.set_tarea_etiquetas(t_inv, [et_dis])
    db.set_tarea_etiquetas(t_wir, [et_dis])
    db.set_tarea_etiquetas(t_kit, [et_dis])
    db.set_tarea_etiquetas(t_api, [et_back])
    db.set_tarea_etiquetas(t_fro, [et_front])
    db.set_tarea_etiquetas(t_int, [et_back, et_front])
    db.set_tarea_etiquetas(t_pru, [et_urg])
    db.set_tarea_etiquetas(t_ent, [et_urg])

    # Dependencias (tarea depende de ...)
    db.add_dependencia(t_wir, t_inv)
    db.add_dependencia(t_kit, t_wir)
    db.add_dependencia(t_api, t_kit)
    db.add_dependencia(t_fro, t_kit)
    db.add_dependencia(t_int, t_api)
    db.add_dependencia(t_int, t_fro)
    db.add_dependencia(t_pru, t_int)
    db.add_dependencia(t_ent, t_pru)

    return pid
