Implement the table renderer in `/app/mdtable/`. Read `/app/README.md` for the package layout
and the rendering rules.

Requirements:

- `column_widths(rows)` (in `mdtable/widths.py`): return the display width of each column as the
  width of the widest cell in that column across every row (not just the header).
- `render(rows)` (in `mdtable/render.py`): return the table as aligned `| a | b |` lines (the
  first row is the header), left-justifying every cell to its column width via `column_widths`
  and escaping cells with the provided `mdtable/cells.py` `escape` helper.
- `render_with_align(rows, aligns)` (in `mdtable/render.py`): render the table with a Markdown
  alignment separator row after the header, justifying each column accordingly; raise
  `mdtable.errors.AlignError` when `aligns` does not match the number of columns or names an
  unknown alignment. Every column is widened to at least three characters, and the separator row
  is padded to **exactly the same width as the rendered rows** — so a left-aligned column three
  characters wide is `:--`, a right-aligned one is `--:`, and a centred one is `:-:`. The
  `:---` / `---:` / `:--:` spellings are the shape of these cells, not a fixed length.

- Produce the shipped sample's rendered preview the way the package's release process
  describes in `/app/README.md`, saving it as `/app/preview.md` (trailing newline included);
  it must match what the renderer produces for `/app/mdtable/sample.json`.

Keep the public names and module paths unchanged, and use the provided `cells.py` and `errors.py`.
Python 3 and its standard library are available; no network access or extra packages are needed.
`mdtable/widths.py` and `mdtable/render.py` must be updated.

## Acceptance criteria

The change is complete when all of the following hold:

- column_widths(rows) returns the width of the widest cell in each column across every row, not just the header.
- render(rows) returns aligned | a | b | lines with cells left-justified to their column width via column_widths and escaped with cells.escape.
- render_with_align(rows, aligns) inserts a Markdown alignment separator row after the header (:--- / ---: / :--:) and justifies each column, raising mdtable.errors.AlignError on a length mismatch or an unknown alignment.
- The provided cells.py and errors.py are used, public names and module paths stay unchanged, and the cli integration keeps working.
- The shipped sample's rendered preview is saved as /app/preview.md, matching the renderer's output for /app/mdtable/sample.json with a trailing newline.
