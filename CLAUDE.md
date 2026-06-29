# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos frecuentes

```bash
# Lanzar la app
uv run gproject
uv run gproject --seed          # carga proyecto demo con dependencias e hitos

# Tests
uv run pytest
uv run pytest tests/test_db.py::test_dependencia_y_anticiclo  # test individual

# Debug visual (Textual DevTools)
uv run textual run --dev gproject.app:GProjectApp
```

Los tests de TUI usan SQLite en memoria: `os.environ["GPROJECT_DB"] = "memory"` al inicio del archivo activa la ruta `:memory:` en `config.py`. Los tests de `db.py` usan `Database(":memory:")` directamente vía fixture.

## Arquitectura

TUI de terminal hecha con Textual. `GProjectApp` (`app.py`) abre `MainScreen` como única pantalla con `push_screen`. `MainScreen` contiene `GanttView` y `KanbanView` en paralelo — solo uno es visible a la vez, controlado por `self.vista` (`"gantt"` | `"kanban"`). Se alterna con `v`.

**Modelos de dominio** (`models.py`):
- `Proyecto` → `Tarea` (jerarquía por `parent_id`, un solo nivel) → `Etiqueta` (N:M vía `tarea_etiquetas`)
- `Dependencia`: fin-a-inicio entre tareas del mismo proyecto. El grafo es dirigido acíclico.
- `Tarea.fecha_fin` es calculada (`fecha_inicio + duracion_efectiva - 1`), nunca se persiste.
- `Tarea.duracion_efectiva`: los hitos siempre valen 1 día independientemente de `duracion_dias`.

**Flujo de datos:**
1. `GProjectApp.db` (`db.py` / SQLite) es la única fuente de verdad; `MainScreen` accede a él vía `self.app.db`.
2. Toda acción CRUD pasa por `MainScreen._recargar()`, que vuelve a leer la BD y llama a `GanttView.cargar()` y `KanbanView.cargar()`.
3. Los widgets emiten mensajes (`TareaResaltada`, `AlternarEstado`) que `MainScreen` escucha para actualizar la barra de detalle o escribir en la BD. Ambos widgets definen los mismos dos mensajes.

**`GanttView`** (`widgets/gantt_chart.py`):
- Hereda de `ScrollView` y usa `render_line(y)` — dibuja una línea de terminal a la vez.
- Panel izquierdo fijo (árbol, `PANEL_ANCHO = 32 chars`) + línea de tiempo deslizable, combinados en un solo `Strip` por línea.
- Las filas visibles (`self.filas: list[Fila]`) se reconstruyen en `_reconstruir()` tras cada cambio de datos o zoom. `Fila` agrega nivel de sangría, estado de expansión y progreso ponderado.
- Zoom: 3 niveles en `ZOOM_NIVELES` — Día (1d/3px), Semana (7d/5px), Mes (30d/9px). `self.nivel` indexa el array.
- Los conectores de dependencias se precalculan en `_construir_conectores()` (caracteres box-drawing) y se superponen al renderizar.

**`KanbanView`** (`widgets/kanban_board.py`):
- También hereda de `ScrollView` con `render_line(y)`.
- Tres columnas fijas: `todo` / `doing` / `done`. Ancho igual, separadas por `│`.
- `self.columna` (0-2) y `self.cursor` (fila dentro de la columna activa) son el estado de selección.
- ←/→ cambia de columna; ↑/↓ mueve el cursor dentro de la columna.

**`scheduling.py` (CPM):**
- `calcular_cpm(tareas, deps)` devuelve `dict[int, ScheduleInfo]` con ES/EF/LS/LF, holgura y `critica`.
- Algoritmo: orden topológico (Kahn) → pase hacia adelante (ES/EF) → pase hacia atrás (LF/LS). Holgura = LS − ES; crítica si holgura == 0.
- Se llama dos veces en cada recarga: desde `GanttView.cargar()` (colorear barras) y desde `MainScreen._actualizar_detalle()` (mostrar holgura en el pie).

**Modales** (`modals/`):
- Todos son `ModalScreen[T]` que se abren con `app.push_screen(Modal(...), callback)`.
- El callback recibe el valor de `dismiss()` o `None` si el usuario cancela.
- `TaskForm`: formulario de tarea; devuelve `dict` con campos incluyendo `"etiquetas": list[str]`.
- `DependencyModal`: gestión de dependencias; devuelve `{"add": id}` o `{"remove": id}` para que `MainScreen` aplique el cambio y reabra el modal.
- `ExportModal`: elige el formato de exportación (CSV / Excel); devuelve `{"formato": "csv" | "xlsx"}`.

**Exportación de tareas** (`export.py`):
- La tecla `x` abre `ExportModal`; según el formato, `export.exportar_csv(tareas, deps, ruta)` o `export.exportar_xlsx(...)` escribe la tabla de tareas en el directorio actual.
- La tabla respeta el orden jerárquico del árbol (DFS por `orden, id`) con una columna `Nivel`. CSV usa `utf-8-sig` (Excel lee bien los acentos); el `.xlsx` usa `openpyxl`.

**`db.py`:**
- `update_tarea` sincroniza automáticamente `progreso=100` y `completado_en` cuando `estado="done"`.
- `delete_tarea` elimina subtareas, etiquetas y dependencias por `ON DELETE CASCADE`.
- `add_dependencia` detecta ciclos con BFS sobre el grafo de sucesores antes de insertar.

## Trampas conocidas

**`Select.NULL` no `Select.BLANK`:** En Textual ≥ 0.80, el centinela de "sin selección" es `Select.NULL`. `Select.BLANK` no existe y provoca `InvalidSelectValueError` al montar el widget. Siempre usar `Select.NULL` como valor por defecto y para comparar (`if val is Select.NULL`).

**`pilot.click("#id")` vs `.press()`:** En tests headless, `pilot.click()` falla con `OutOfBounds` si el botón queda fuera del viewport virtual. Usar `app.screen.query_one("#id", Button).press()` en su lugar.

**`app.query_one()` vs `app.screen.query_one()`:** `MainScreen` se abre con `push_screen`, no es la pantalla por defecto; `app.query_one()` busca en la pantalla base (vacía) y lanza `NoMatches`. Usar siempre `app.screen.query_one()`.

**BD y rutas:** `config.py` lee `$GPROJECT_DB` (`:memory:` si el valor es `"memory"`) y `$GPROJECT_DATA_DIR` para la ruta del archivo. La migración es idempotente vía `PRAGMA user_version`.

**`virtual_size` en `ScrollView`:** Ambos widgets deben actualizar `self.virtual_size` en `on_resize` y tras cada recarga. Si se omite, el scroll queda roto o el widget no se renderiza.
