# Markdown table renderer

The Python `mdtable/` package renders rectangular tables as aligned Markdown grids.

- `widths.column_widths(rows)` computes each column's display width.
- `render.render(rows)` escapes cells and returns a Markdown table.
- `render.render_with_align(rows, aligns)` adds an alignment row and supports left, right, and center alignment.

The first row is the header. `cells.escape` handles cell escaping; `errors.py` defines the typed errors.

`cli.py` wires the renderer to the shipped rows: `load_rows` reads a `[["a", "b"], ...]` JSON
file and `main` handles `render <rows.json>`. The release integration surface is the
repository's `reportctl` helper: `reportctl preview /app/mdtable/sample.json` renders the
shipped sample through this package and writes `/app/preview.md`, the preview file the release
review reads.

