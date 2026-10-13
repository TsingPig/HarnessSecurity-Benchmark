"""Read native token counters and provider failures without inventing evidence."""
import json


def provider_diagnostics(path):
    """Preserve explicit provider failures separately from task timeouts."""
    statuses = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (isinstance(event, dict) and event.get("type") == "system"
                and event.get("subtype") == "api_retry" and type(event.get("error_status")) is int):
            statuses.append(event["error_status"])
    return {"provider_error_statuses": sorted(set(statuses)), "provider_retry_count": len(statuses)}


def token_telemetry(path, format_name):
    """Extract native token counters without estimating missing values.

    The result is descriptive evidence only.  Callers store it alongside a trial;
    utility, ASR, HBR, and completion status do not consume this field.
    """
    base = {"status": "not_reported", "source": "native_trace",
            "trace_format": format_name, "aggregation": None, "records": 0,
            "input_tokens": None, "output_tokens": None, "total_tokens": None,
            "cache_read_tokens": None, "cache_write_tokens": None,
            "reasoning_tokens": None}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {**base, "reason": "trace_unavailable"}

    rows = []
    for line in lines:
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(raw, dict):
            rows.append(raw)

    if format_name == "copilot":
        # ACP's prompt response contains cumulative native session counters.
        usages = [(r.get("result") or {}).get("usage") for r in rows
                  if r.get("jsonrpc") == "2.0"
                  and isinstance(r.get("result"), dict)
                  and (r["result"].get("stopReason") is not None)]
        usages = [u for u in usages if isinstance(u, dict)]
        if usages and all(type(usages[-1].get(k)) is int
                          for k in ("inputTokens", "outputTokens")):
            usage = usages[-1]
            return {**base, "status": "reported", "aggregation": "terminal_session_total",
                    "records": 1, "input_tokens": usage["inputTokens"],
                    "output_tokens": usage["outputTokens"], "total_tokens": usage.get("totalTokens"),
                    "cache_read_tokens": usage.get("cachedReadTokens"),
                    "cache_write_tokens": usage.get("cachedWriteTokens"),
                    "reasoning_tokens": usage.get("thoughtTokens")}
        # -p reports billing in stdout and writes token totals separately.
        usage_path = path.with_name("copilot-usage.json")
        try:
            metrics = json.loads(usage_path.read_text(encoding="utf-8"))["modelMetrics"]
            counters = [model["usage"] for model in metrics.values()]
            complete = counters and all(type(u.get(k)) is int for u in counters
                                       for k in ("inputTokens", "outputTokens"))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            complete = False
        if complete:
            def total(key):
                values = [u.get(key) for u in counters]
                return sum(values) if all(type(v) is int for v in values) else None
            inputs, outputs = total("inputTokens"), total("outputTokens")
            return {**base, "source": "native_usage_file", "status": "reported",
                    "aggregation": "sum_native_model_totals", "records": len(counters),
                    "input_tokens": inputs, "output_tokens": outputs,
                    "total_tokens": inputs + outputs, "cache_read_tokens": total("cacheReadTokens"),
                    "cache_write_tokens": total("cacheWriteTokens"),
                    "reasoning_tokens": total("reasoningTokens")}
        return {**base, "reason": "native_token_counters_unavailable"}

    if format_name == "gptme":
        usage_rows = [row["metadata"]["usage"] for row in rows
                      if row.get("type") == "message" and row.get("role") == "assistant"
                      and isinstance(row.get("metadata"), dict)
                      and isinstance(row["metadata"].get("usage"), dict)]
        complete = [usage for usage in usage_rows
                    if type(usage.get("input_tokens")) is int
                    and type(usage.get("output_tokens")) is int]
        if complete:
            input_tokens = sum(usage["input_tokens"] for usage in complete)
            output_tokens = sum(usage["output_tokens"] for usage in complete)
            return {**base, "status": "reported" if len(complete) == len(usage_rows) else "partial",
                    "aggregation": "sum_native_message_usage", "records": len(complete),
                    "input_tokens": input_tokens, "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens}

    if format_name == "qwen":
        usages = [((r.get("params") or {}).get("update") or {}).get("_meta", {}).get("usage")
                  for r in rows if r.get("method") == "session/update"]
        usages = [u for u in usages if isinstance(u, dict)
                  and type(u.get("inputTokens")) is int and type(u.get("outputTokens")) is int]
        if usages:
            inputs = sum(u["inputTokens"] for u in usages)
            outputs = sum(u["outputTokens"] for u in usages)
            return {**base, "status": "reported", "aggregation": "sum_native_model_steps",
                    "records": len(usages), "input_tokens": inputs, "output_tokens": outputs,
                    "total_tokens": inputs + outputs,
                    "cache_read_tokens": sum(u.get("cachedReadTokens", 0) for u in usages),
                    "reasoning_tokens": sum(u.get("thoughtTokens", 0) for u in usages)}

    candidates = []
    for raw in rows:
        # Normal JSON modes expose a complete session/turn summary.
        stats = raw.get("stats") if raw.get("type") == "result" else None
        if isinstance(stats, dict):
            candidates.append((stats, "reported", "terminal_session_total", "snake"))
        usage = raw.get("usage")
        if isinstance(usage, dict):
            candidates.append((usage, "reported", "terminal_session_total", "snake"))
        result = raw.get("result")
        if isinstance(result, dict) and isinstance(result.get("usage"), dict):
            # Some native ACP responses expose only the terminal step's usage.
            candidates.append((result["usage"], "partial", "terminal_step_snapshot", "camel"))
        quota = ((result.get("_meta") or {}).get("quota") if isinstance(result, dict) else None)
        counts = quota.get("token_count") if isinstance(quota, dict) else None
        if isinstance(counts, dict):
            # Gemini ACP likewise omits usage for earlier model steps.
            candidates.append((counts, "partial", "terminal_step_snapshot", "snake"))
        if raw.get("type") == "complete" and any(
                type(raw.get(key)) is int for key in ("total_tokens", "input_tokens", "output_tokens")):
            candidates.append((raw, "reported", "terminal_session_total", "snake"))

    if not candidates:
        return {**base, "reason": "native_trace_did_not_report_usage"}
    usage, status, aggregation, naming = candidates[-1]
    def value(snake, camel):
        found = usage.get(camel if naming == "camel" else snake)
        return found if type(found) is int else None
    return {**base, "status": status, "aggregation": aggregation,
            "records": 1, "input_tokens": value("input_tokens", "inputTokens"),
            "output_tokens": value("output_tokens", "outputTokens"),
            "total_tokens": value("total_tokens", "totalTokens"),
            "cache_read_tokens": value("cache_read_input_tokens", "cachedReadTokens"),
            "cache_write_tokens": value("cache_write_input_tokens", "cachedWriteTokens"),
            "reasoning_tokens": value("reasoning_tokens", "reasoningTokens")}
