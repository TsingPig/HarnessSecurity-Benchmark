"""Self-test adapter for the Node verifier; the formal verifier remains verify.js."""
import os
import subprocess
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))


def load():
    return APP


def check(app):
    result = subprocess.run(
        ["node", str(Path(__file__).with_name("verify.js"))],
        env={**os.environ, "RQ2_APP": str(app),
             "RQ2_VERIFIER_LOG": str(app / ".verifier")},
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ValueError(result.stdout.strip() or result.stderr.strip())
