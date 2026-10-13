"""Extract the final assistant text from pinned harness JSONL traces.

Only assistant-message events are eligible. In particular, a task document
printed by a tool cannot spoof the answer used by an offline utility verifier.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def extract_final_answer(path: Path, trace_format: str) -> str | None:
    final: str | None = None
    gemini_parts: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            try:
                event = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(event, dict):
                continue
            kind = event.get("type")
            if trace_format == "codex":
                item = event.get("item")
                if (kind == "item.completed" and isinstance(item, dict)
                        and item.get("type") == "agent_message"
                        and isinstance(item.get("text"), str)):
                    final = item["text"]
            elif trace_format in ("qwen", "copilot") and event.get("method") == "session/update":
                update = (event.get("params") or {}).get("update") or {}
                if update.get("sessionUpdate") in ("tool_call", "tool_call_update"):
                    gemini_parts.clear()
                elif update.get("sessionUpdate") == "agent_message_chunk":
                    content = update.get("content") or {}
                    if content.get("type") == "text" and isinstance(content.get("text"), str):
                        gemini_parts.append(content["text"])
            elif trace_format == "copilot":
                data = event.get("data") or {}
                if (kind == "assistant.message" and isinstance(data.get("content"), str)
                        and data["content"].strip()):
                    final = data["content"]
            elif trace_format in ("claude", "qwen"):
                message = event.get("message")
                if kind == "assistant" and isinstance(message, dict):
                    blocks = message.get("content")
                    if isinstance(blocks, list):
                        text = "\n".join(block["text"] for block in blocks
                                         if isinstance(block, dict) and block.get("type") == "text"
                                         and isinstance(block.get("text"), str))
                        if text:
                            final = text
            elif trace_format == "gptme":
                if (kind == "message" and event.get("role") == "assistant"
                        and isinstance(event.get("content"), str)):
                    content = event["content"]
                    visible = re.sub(r"^\s*<think>.*?</think>\s*", "", content, flags=re.DOTALL).strip()
                    # gptme finishes by issuing @complete after its user-facing
                    # answer. The completion call is an assistant event, but is
                    # not the answer the user receives.
                    if visible and not re.fullmatch(r"@complete\([^)]*\):\s*\{\s*\}", visible):
                        final = content
            elif trace_format == "gemini":
                if kind in ("tool_use", "tool_result"):
                    gemini_parts.clear()
                elif kind == "message" and event.get("role") == "assistant":
                    content = event.get("content")
                    if isinstance(content, str):
                        if event.get("delta") is False:
                            gemini_parts = [content]
                        else:
                            gemini_parts.append(content)
    if trace_format == "gemini":
        final = "".join(gemini_parts)
    elif trace_format in ("qwen", "copilot") and gemini_parts:
        final = "".join(gemini_parts)
    return final[:65536] if final else None
