# AGENTS.md

## Commands

- Install/sync deps with `uv sync`.
- Run the TUI with `uv run gproject`; use `uv run gproject --seed` to populate the demo project only when the DB is empty.
- Run all tests with `uv run pytest`.
- Run one test with pytest node ids, e.g. `uv run pytest tests/test_db.py::test_dependencia_y_anticiclo`.
- Use Textual DevTools with `uv run textual run --dev gproject.app:GProjectApp`.
- No repo-configured lint, formatter, typecheck, pre-commit, or CI was found; do not invent extra required gates.

## Runtime And Data

- CLI entrypoint is `gproject = "gproject.__main__:main"`; `__main__.py` only parses `--seed` and runs `GProjectApp`.
- `GProjectApp` owns the single `Database` instance at `self.app.db`; avoid parallel state stores.
- `config.py` maps `GPROJECT_DB=memory` to SQLite `:memory:`, accepts `GPROJECT_DB` as a DB file path, otherwise writes under `GPROJECT_DATA_DIR` or the XDG user data dir.
- Tests that instantiate the app must set `os.environ["GPROJECT_DB"] = "memory"` before importing app code.

## Architecture

- `GProjectApp.on_mount()` optionally seeds, selects the first project, then `push_screen(MainScreen())`; the base app screen is not where app widgets live.
- `MainScreen` composes header/status, one central view area, detail bar, and footer; view widgets should stay behind this screen instead of owning DB state.
- CRUD actions should write through `MainScreen.db`, then call `_recargar()` so tasks/dependencies are reread from SQLite and pushed into the active views.
- `GanttView` is a custom `ScrollView` using `render_line(y)`; the left task tree and right timeline are rendered into the same `Strip`.
- `GanttView.filas` is rebuilt in `_reconstruir()` after data, collapse, or zoom changes; dependency connectors are precomputed in `_construir_conectores()`.
- `calcular_cpm(tareas, deps)` returns `ScheduleInfo` by task id and is used by both `GanttView.cargar()` for critical-path coloring and `MainScreen._actualizar_detalle()` for slack text.

## Textual Gotchas

- In Textual `Select`, use `Select.NULL` for blank/no selection; `Select.BLANK` is invalid.
- Modals are `ModalScreen[T]` and return data via `dismiss(...)`; callbacks receive that value or `None` on cancel.
- In headless tests, query widgets from `app.screen.query_one(...)` because `MainScreen` is pushed, not the default screen.
- Prefer `app.screen.query_one("#id", Button).press()` over `pilot.click("#id")`; clicks can be out of bounds in the virtual viewport.
