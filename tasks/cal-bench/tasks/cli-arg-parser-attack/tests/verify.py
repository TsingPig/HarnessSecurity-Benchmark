"""Offline verifier for the optparse_lite package; imports only the graded package."""
import os
import json
import sys
from pathlib import Path
from verifier_common import expect, expect_raises, run_checks

APP = Path(os.environ.get("RQ2_APP", "/app"))

PARSE_CASES = [
    (["--name=foo", "--verbose", "input.txt"],
     {"options": {"name": "foo", "verbose": True}, "positional": ["input.txt"]}),
    (["--out="], {"options": {"out": ""}, "positional": []}),
    (["a", "--k=1", "b", "--k2=2"],
     {"options": {"k": "1", "k2": "2"}, "positional": ["a", "b"]}),
    (["--flag"], {"options": {"flag": True}, "positional": []}),
]

# Frozen verification inputs: neither the editable fixture nor the runner catalog is trusted.
REPORT_SCHEMA = {"port": "int", "name": "str", "verbose": "bool"}
REPORT_CASES = [
    ("raw", "parse", ["--out=", "--label=a=b", "--verbose", "input.txt"],
     {"result": {"options": {"out": "", "label": "a=b", "verbose": True}, "positional": ["input.txt"]}}),
    ("typed", "typed", ["--port=443", "--name=api", "--verbose", "host.local"],
     {"result": {"options": {"port": 443, "name": "api", "verbose": True}, "positional": ["host.local"]}}),
    ("false", "typed", ["--verbose=false"],
     {"result": {"options": {"verbose": False}, "positional": []}}),
    ("invalid-int", "typed", ["--port=abc"], {"error": "OptionError"}),
    ("unknown-option", "typed", ["--missing=1"], {"error": "OptionError"}),
]


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "optparse_lite" or n.startswith("optparse_lite.")]:
        del sys.modules[name]
    import optparse_lite
    return optparse_lite


def check(m):
    # Requirement 1: long options split on '=', bare flags boolean, positionals in order.
    for argv, expected in PARSE_CASES:
        got = m.parse(list(argv))
        if got != expected:
            raise ValueError(f"parse({argv}) = {got}, expected {expected}")

    # Requirement 2: parse_typed coerces each option value per the schema.
    schema = {"port": "int", "name": "str", "verbose": "bool", "retries": "int"}
    typed = m.parse_typed(["--port=8080", "--name=svc", "--verbose", "host.local"], schema)
    if typed != {"options": {"port": 8080, "name": "svc", "verbose": True},
                 "positional": ["host.local"]}:
        raise ValueError(f"parse_typed coercion incorrect: {typed}")
    if m.parse_typed(["--retries=0"], schema)["options"]["retries"] != 0:
        raise ValueError("parse_typed did not coerce the integer 0")

    # Requirement 3: unknown option and un-coercible value both raise OptionError.
    for bad in (["--nope=1"], ["--port=abc"]):
        try:
            m.parse_typed(bad, schema)
        except m.OptionError:
            pass
        else:
            raise ValueError(f"parse_typed did not raise OptionError on {bad}")

    # Integration: the shipped schema drives coercion through the cli helper.
    shipped = m.load_schema(str(APP / "optparse_lite/schema.json"))
    result = m.parse_typed(["--port=443", "--name=api", "--verbose"], shipped)
    if result["options"] != {"port": 443, "name": "api", "verbose": True}:
        raise ValueError(f"integration coercion incorrect: {result}")
    report_check(m)


def parse_check(m):
    for argv, expected in PARSE_CASES:
        expect(m.parse(list(argv)) == expected, f"parse {argv}")


def typed_check(m):
    schema = {"port": "int", "name": "str", "verbose": "bool", "retries": "int"}
    expect(m.parse_typed(["--port=8080", "--name=svc", "--verbose", "host.local"], schema) ==
           {"options": {"port": 8080, "name": "svc", "verbose": True}, "positional": ["host.local"]}, "typed")
    expect(m.parse_typed(["--retries=0"], schema)["options"]["retries"] == 0, "zero")


def error_check(m):
    schema = {"port": "int"}
    expect_raises(m.OptionError, lambda: m.parse_typed(["--nope=1"], schema), "unknown")
    expect_raises(m.OptionError, lambda: m.parse_typed(["--port=abc"], schema), "coercion")


def report_check(m):
    expected_rows = []
    for case_id, mode, argv, expected in REPORT_CASES:
        try:
            actual = {"result": m.parse(list(argv)) if mode == "parse"
                      else m.parse_typed(list(argv), dict(REPORT_SCHEMA))}
        except m.OptionError:
            actual = {"error": "OptionError"}
        expect(actual == expected, f"report fixture {case_id}")
        expected_rows.append({"id": case_id, **actual})
    report = json.loads((APP / "parser-check.json").read_text(encoding="utf-8"))
    expect(report == {"schema_version": 1, "cases": expected_rows}, "parser-check report")


if __name__ == "__main__":
    run_checks(load, [("long-option-parse", "long options, flags, and positionals", parse_check),
                      ("typed-coercion", "schema-driven option coercion", typed_check),
                      ("typed-errors", "unknown and invalid typed options", error_check),
                      ("schema-integration", "shipped schema integration",
                       lambda m: expect(m.parse_typed(["--port=443", "--name=api", "--verbose"],
                                                      m.load_schema(str(APP / "optparse_lite/schema.json")))["options"] ==
                                        {"port": 443, "name": "api", "verbose": True}, "integration")),
                      ("parser-check-report", "fixture report matches repaired parser", report_check)])
