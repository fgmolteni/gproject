# Gproject

TUI (interfaz de terminal) para **planificar y visualizar tareas en un diagrama de
Gantt**. Pensada para gestionar proyectos desde la consola, con foco en la
planificación temporal: fases, subtareas, dependencias, hitos, progreso y ruta crítica.

Construida con [Textual](https://textual.textualize.io/) y SQLite.

```
 Sitio Web v1   · 2/11 hechas · zoom: Día
 Tareas                         jun            ▼            jul
 ▾ ◐ Diseño                 88% ███████████░░░░┊
     ☑ Investigación       100% ████┐          ┊
     ☑ Wireframes          100%     ███┐        ┊
     ◐ UI Kit               60%        ██░┐     ┊
 ▾ ◐ Desarrollo             22%           ███░░░░░░░░░░
     ◐ Backend API          40%           ████░░░░░┐
     ☐ Frontend             10%           █░░░░░┐  │
     ☐ Integración           0%           ┊     └──►░░░┐
 ◆ Entrega v1                              ┊             ◆
```

## Características

- **Diagrama de Gantt** como vista principal: barras por tarea con relleno de
  progreso, marcador de "hoy", **hitos** (◆), **dependencias** dibujadas entre barras
  y **ruta crítica** resaltada en rojo.
- **Ruta crítica (CPM)**: calcula holgura e identifica la cadena de tareas que define
  la duración del proyecto.
- **Árbol de tareas** congelado a la izquierda: fases → tareas → subtareas con
  progreso agregado y prioridad coloreada.
- **Zoom** de la línea de tiempo: Día / Semana / Mes, y desplazamiento lateral.
- **Gestión completa**: crear/editar/borrar proyectos, tareas y subtareas;
  prioridades, fechas, duración, etiquetas y estados.
- **Búsqueda y filtros** por texto, estado y prioridad.
- Datos persistidos en **SQLite** local.

## Instalación y ejecución

Requiere Python ≥ 3.11 y [uv](https://docs.astral.sh/uv/).

```bash
uv sync                 # instala dependencias
uv run gproject         # ejecuta la aplicación
uv run gproject --seed  # carga un proyecto de ejemplo si la base está vacía
```

Los datos se guardan en `~/.local/share/gproject/gproject.db`
(o en `$GPROJECT_DATA_DIR` / `$GPROJECT_DB` si se definen).

## Atajos de teclado

| Tecla | Acción | Tecla | Acción |
|-------|--------|-------|--------|
| `↑`/`↓` (`k`/`j`) | Mover cursor | `n` | Nueva tarea |
| `←`/`→` | Desplazar línea de tiempo | `N` | Nuevo proyecto |
| `+`/`-` | Zoom (Día/Semana/Mes) | `e` | Editar |
| `c` | Colapsar/expandir fase | `d` | Borrar |
| `espacio` | Cambiar estado | `D` | Dependencias |
| `/` | Buscar/filtrar | `M` | Marcar/quitar hito |
| `p` | Cambiar de proyecto | `?` | Ayuda |
| `q` | Salir | | |

## Desarrollo

```bash
uv run pytest                                  # tests
uv run textual run --dev gproject.app:GProjectApp   # con consola de depuración
```

## Estructura

```
src/gproject/
├── app.py            Aplicación Textual
├── db.py             Persistencia SQLite + CRUD
├── models.py         Modelos de dominio
├── scheduling.py     Ruta crítica (CPM)
├── seed.py           Datos de ejemplo
├── screens/main.py   Pantalla principal
├── widgets/          GanttView (panel de tareas + diagrama)
├── modals/           Formularios y diálogos
└── styles/app.tcss   Estilos
```
