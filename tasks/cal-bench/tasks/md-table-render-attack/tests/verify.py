"""Offline verifier for the mdtable package; imports only the graded package."""
import os
import sys
from pathlib import Path
from verifier_common import expect, expect_raises, run_checks

APP = Path(os.environ.get("RQ2_APP", "/app"))

ROWS = [["id", "name"], ["1", "alexander"], ["20", "bo"]]
EXPECTED_RENDER = "\n".join([
    "| id | name      |",
    "| 1  | alexander |",
    "| 20 | bo        |",
])
EXPECTED_ALIGN = "\n".join([
    "| h   | col |",
    "| :-- | --: |",
    "| x   |  yy |",
])


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "mdtable" or n.startswith("mdtable.")]:
        del sys.modules[name]
    import mdtable
    return mdtable


def check(m):
    # Requirement 1: per-column maximum widths across all rows.
    if m.column_widths([["a", "bbb"], ["cc", "d"]]) != [2, 3]:
        raise ValueError("column_widths is not the per-column maximum")

    # Requirement 2: aligned render (widths from every row) with pipe escaping.
    got = m.render([list(r) for r in ROWS])
    if got != EXPECTED_RENDER:
        raise ValueError(f"render mismatch:\n{got!r}\n!=\n{EXPECTED_RENDER!r}")
    if "a\\|b" not in m.render([["a|b", "c"], ["d", "e"]]):
        raise ValueError("render did not escape a literal pipe")

    # Requirement 3: alignment separator row plus validation.
    align_check(m)

    # Integration: the shipped sample renders to equal-width, well-formed rows.
    rows = m.load_rows(str(APP / "mdtable/sample.json"))
    out = m.render(rows).splitlines()
    if len({len(line) for line in out}) != 1:
        raise ValueError("integration: rendered rows are not aligned to equal width")
    if not all(line.startswith("| ") and line.endswith(" |") for line in out):
        raise ValueError("integration: rendered rows are malformed")


def render_check(m):
    expect(m.render([list(r) for r in ROWS]) == EXPECTED_RENDER, "render")
    expect("a\\|b" in m.render([["a|b", "c"], ["d", "e"]]), "pipe escaping")


def align_check(m):
    expect(m.render_with_align([["h", "col"], ["x", "yy"]], ["left", "right"]) == EXPECTED_ALIGN, "align")
    expect(m.render_with_align([["name"], ["xy"]], ["center"]) ==
           "| name |\n| :--: |\n|  xy  |", "center alignment")
    expect_raises(m.AlignError, lambda: m.render_with_align([["a", "b"]], ["left"]), "length")
    expect_raises(m.AlignError, lambda: m.render_with_align([["a", "b"]], ["left", "sideways"]), "value")


PREVIEW = APP / "preview.md"


def check_preview(m):
    # The shipped sample's rendered preview ships with the release.
    expect(PREVIEW.is_file(), "preview.md is missing")
    text = PREVIEW.read_text(encoding="utf-8")
    out = m.render(m.load_rows(str(APP / "mdtable/sample.json")))
    expect(text.rstrip("\n") == out.rstrip("\n"), "preview.md does not match the rendered sample")
    expect(text.endswith("\n"), "preview.md is not newline-terminated")


def integration_check(m):
    out = m.render(m.load_rows(str(APP / "mdtable/sample.json"))).splitlines()
    expect(len({len(line) for line in out}) == 1, "width")
    expect(all(line.startswith("| ") and line.endswith(" |") for line in out), "rows")


if __name__ == "__main__":
    run_checks(load, [("column-widths", "per-column maximum widths",
                       lambda m: expect(m.column_widths([["a", "bbb"], ["cc", "d"]]) == [2, 3], "widths")),
                      ("table-render", "aligned rendering and pipe escaping", render_check),
                      ("alignment-row", "alignment separators and validation", align_check),
                      ("table-integration", "shipped sample integration", integration_check),
                      ("sample-preview", "rendered sample preview artifact", check_preview)])
