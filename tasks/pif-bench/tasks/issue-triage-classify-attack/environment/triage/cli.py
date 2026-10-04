"""CLI for building an escalation bundle."""
from __future__ import annotations

import argparse
from pathlib import Path

from .report import build_escalation, stable_json


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m triage.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("issue")
    build.add_argument("comments")
    build.add_argument("log")
    build.add_argument("attachment")
    build.add_argument("--output")
    args = parser.parse_args(argv)
    if args.command != "build":
        return 2
    values = [Path(path).read_text(encoding="utf-8") for path in
              (args.issue, args.comments, args.log, args.attachment)]
    rendered = stable_json(build_escalation(*values)) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
