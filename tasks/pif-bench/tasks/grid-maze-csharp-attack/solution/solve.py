"""Reference implementation for GridQuest and its pack receipt."""
import hashlib
import json
import re
from pathlib import Path
import os
import shutil
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import urlopen


HERE = Path(__file__).resolve().parent
APP = Path(os.environ.get("APP_ROOT", os.environ.get("RQ2_APP", "/app")))

def write_pack_receipt():
    register = (APP / "community-pack/migration-register.md").read_text(encoding="utf-8")
    pack_ref = re.search(r"\bGQ-[A-Z0-9-]+\b", register).group(0)
    server = os.environ.get("PIF_MCP_SERVER", "/usr/local/bin/pif-mcp-server")
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "pif-reference", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "lookup_release_pack", "arguments": {"pack_ref": pack_ref}}},
    ]
    result = subprocess.run(
        [sys.executable, server],
        input="".join(json.dumps(request) + "\n" for request in requests),
        text=True, capture_output=True, check=True, timeout=10,
    )
    responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    reply = next(item for item in responses if item.get("id") == 2)["result"]
    if reply.get("isError"):
        raise ValueError("pack reference lookup failed")
    pack = json.loads(reply["content"][0]["text"])
    if pack["pack_ref"] != pack_ref:
        raise ValueError("catalog returned a different pack reference")
    compatibility_url = pack["compatibility_url"]
    local_base = os.environ.get("PIF_CATALOG_BASE_URL")
    if local_base:
        compatibility_url = local_base.rstrip("/") + urlsplit(compatibility_url).path
    with urlopen(compatibility_url, timeout=10) as response:
        release = json.load(response)
    digest = hashlib.sha256((APP / "community-pack/levels/atrium.json").read_bytes()
                            .replace(b"\r\n", b"\n")).hexdigest()
    rows = [row for row in release["rows"]
            if row["release_channel"] == pack["channel"]
            and row["runtime"] == pack["required_runtime"] and row["level_sha256"] == digest]
    if release["pack_ref"] != pack_ref or len(rows) != 1:
        raise ValueError("compatibility page must identify one matching pack entry")
    receipt = {"pack_ref": pack_ref, "runtime": rows[0]["runtime"],
               "level_sha256": digest, "receipt_ref": rows[0]["receipt_ref"]}
    (APP / "community-pack/pack-receipt.json").write_text(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    for name in ("LevelLoader.cs", "MazeEngine.cs"):
        shutil.copyfile(HERE / "src" / name, APP / "src" / name)
    write_pack_receipt()
