# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos frecuentes

```bash
# Lanzar la app
uv run gproject
uv run gproject --seed          # carga proyecto demo con dependencias e hitos

# Tests
uv run pytest
uv run pytest tests/test_db.py::test_anticiclo  # test individual

# Debug visual (Textual DevTools)
uv run textual run --dev gproject.app:GProjectApp
```

Los tests usan SQLite en memoria: `os.environ["GPROJECT_DB"] = "memory"` al principio de cada archivo de test activa la ruta `:memory:` en `config.py`.

## Arquitectura

La app es un `App` de Textual (`app.py`) que abre `MainScreen` como pantalla principal. `MainScreen` contiene únicamente un `GanttView` (widget central) flanqueado por barras estáticas superior e inferior. No hay panel lateral separado — el árbol de tareas está integrado dentro de `GanttView`.

**Flujo de datos:**
1. `GProjectApp.db` (`db.py` / SQLite) es la única fuente de verdad; `MainScreen` accede a él vía `self.app.db`.
2. Toda acción CRUD pasa por `MainScreen._recargar()`, que vuelve a leer la BD y llama a `GanttView.cargar()`.
3. `GanttView` emite mensajes (`TareaResaltada`, `AlternarEstado`) que `MainScreen` escucha para actualizar la barra de detalle o escribir en la BD.

**`GanttView` (widget crítico):**
- Hereda de `ScrollView` y usa el patrón `render_line(y)` — dibuja una línea del terminal a la vez.
- El panel izquierdo (árbol, 32 chars) y la línea de tiempo derecha se combinan en un solo `Strip` por línea.
- Las filas visibles (`self.filas: list[Fila]`) se reconstruyen en `_reconstruir()` tras cada cambio de datos o zoom.
- Los conectores de dependencias se precalculan en `_construir_conectores()` y se superponen al renderizar.

**`scheduling.py` (CPM):**
- `calcular_cpm(tareas, deps)` devuelve `dict[int, ScheduleInfo]` con ES/EF/LS/LF, holgura y `critica`.
- Se llama dos veces en cada recarga: una desde `GanttView.cargar()` (para colorear la ruta crítica en las barras) y otra desde `MainScreen._actualizar_detalle()` (para mostrar holgura en el pie).

**Modales:**
- Todos son `ModalScreen[T]` que se abren con `app.push_screen(Modal(...), callback)`.
- El callback recibe el valor de `dismiss()` o `None` si el usuario cancela.

## Trampas conocidas

**`Select.NULL` no `Select.BLANK`:** En Textual ≥ 0.80, el centinela de "sin selección" es `Select.NULL`. `Select.BLANK` no existe y provoca `InvalidSelectValueError` al montar el widget. Siempre usar `Select.NULL` como valor por defecto y para comparar (`if val is Select.NULL`).

**`pilot.click("#id")` vs `.press()`:** En tests headless, `pilot.click()` falla con `OutOfBounds` si el botón queda fuera del viewport virtual. Usar `app.screen.query_one("#id", Button).press()` en su lugar.

**`app.query_one()` vs `app.screen.query_one()`:** `MainScreen` se abre con `push_screen`, no es la pantalla por defecto; `app.query_one()` busca en la pantalla base (vacía) y lanza `NoMatches`. Usar siempre `app.screen.query_one()`.

**BD y rutas:** `config.py` lee `$GPROJECT_DB` (`:memory:` si el valor es `"memory"`) y `$GPROJECT_DATA_DIR` para la ruta del archivo. La migración es idempotente vía `PRAGMA user_version`.
