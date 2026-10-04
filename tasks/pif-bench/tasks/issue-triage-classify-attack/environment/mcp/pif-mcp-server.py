#!/usr/bin/env python3
"""Small stdio JSON-RPC MCP catalog used by the PIF task."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPLIES = Path(os.environ.get("PIF_MCP_REPLIES_FILE", "/usr/local/share/pif-mcp-replies.json"))
LOG = Path(os.environ.get("PIF_MCP_LOG_PATH", "/var/spool/pif/catalog-invocations.jsonl"))
SUPPORTED = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}


def record(**fields):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"component": "pif-mcp-catalog", "transport": "stdio-jsonrpc",
                                "ts": time.time(), **fields}, sort_keys=True) + "\n")


def config():
    return json.loads(REPLIES.read_text(encoding="utf-8"))


def lookup(spec, arguments):
    for row in spec.get("responses", {}).get(arguments.get("_tool", ""), []):
        when = row.get("when", {})
        if all(arguments.get(key) == value for key, value in when.items()):
            return row.get("result")
    return None


def serve():
    initialized = False
    for line in sys.stdin:
        try:
            request = json.loads(line)
            identity = request.get("id")
            method = request.get("method")
            params = request.get("params") or {}
            error = None
            if method == "initialize":
                version = params.get("protocolVersion")
                if version not in SUPPORTED:
                    error = {"code": -32602, "message": "Unsupported protocol version"}
                else:
                    initialized = True
                    result = {"protocolVersion": version, "capabilities": {"tools": {}},
                              "serverInfo": {"name": "catalog", "version": "1.0.0"}}
                    record(action="initialize", event="delivered", protocol_version=version)
            elif method == "notifications/initialized" and initialized:
                continue
            elif method == "ping":
                result = {}
            elif not initialized:
                error = {"code": -32002, "message": "Initialization required"}
            elif method == "tools/list":
                result = {"tools": config()["tools"]}
                record(action="discover-tools", event="delivered")
            elif method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                spec = config()
                tool = next((item for item in spec["tools"] if item.get("name") == name), None)
                if tool is None or not isinstance(arguments, dict):
                    error = {"code": -32602, "message": "Unknown tool or invalid arguments"}
                else:
                    resolved = lookup(spec, {**arguments, "_tool": name})
                    record(action="catalog-lookup", event="delivered" if resolved is not None else "rejected",
                           tool=name, arguments=arguments)
                    result = {"content": [{"type": "text", "text": json.dumps(
                        resolved if resolved is not None else {"error": "record not found"},
                        sort_keys=True, ensure_ascii=False)}], "isError": resolved is None}
            else:
                error = {"code": -32601, "message": "Method not found"}
            if identity is not None:
                response = {"jsonrpc": "2.0", "id": identity,
                            "error" if error else "result": error or result}
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except (ValueError, TypeError, AttributeError, OSError) as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None,
                              "error": {"code": -32700, "message": str(exc)}}), flush=True)


if __name__ == "__main__":
    serve()
