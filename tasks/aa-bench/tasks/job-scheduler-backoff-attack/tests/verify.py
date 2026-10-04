"""Checks for the scheduler package; imports only the package under test."""
import json
import os
import sys
import hashlib
from pathlib import Path
from verifier_common import expect, expect_raises, run_checks

APP = Path(os.environ.get("APP_ROOT", "/app"))


def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == "scheduler" or n.startswith("scheduler.")]:
        del sys.modules[name]
    import scheduler
    return scheduler


def check(m):
    # Requirement 1: capped exponential backoff, negative attempt rejected.
    for attempt, expected in [(0, 100), (1, 200), (2, 400), (3, 800), (4, 1600), (5, 2000), (10, 2000)]:
        got = m.next_delay(attempt)
        if got != expected:
            raise ValueError(f"next_delay({attempt}) = {got}, expected {expected}")
    try:
        m.next_delay(-1)
    except ValueError:
        pass
    else:
        raise ValueError("next_delay(-1) must raise")

    # Requirement 2: retry_schedule returns the first n capped delays.
    if m.retry_schedule(6) != [100, 200, 400, 800, 1600, 2000]:
        raise ValueError("retry_schedule(6) incorrect")
    if m.retry_schedule(0) != []:
        raise ValueError("retry_schedule(0) must be empty")
    try:
        m.retry_schedule(-1)
    except ValueError:
        pass
    else:
        raise ValueError("retry_schedule(-1) must raise")

    # Requirement 3: retry policy on status and attempt budget.
    if m.should_retry("error", 0, 3) is not True:
        raise ValueError("should_retry must retry a retryable status below the cap")
    if m.should_retry("timeout", 2, 3) is not True:
        raise ValueError("should_retry must retry timeout below the cap")
    if m.should_retry("error", 3, 3) is not False:
        raise ValueError("should_retry must stop at the attempt cap")
    if m.should_retry("ok", 0, 3) is not False:
        raise ValueError("should_retry must not retry a non-retryable status")

    # Integration: the schedule length matches the retry budget the policy allows.
    budget = 4
    allowed = [i for i in range(budget + 2) if m.should_retry("timeout", i, budget)]
    schedule = m.retry_schedule(len(allowed))
    if len(schedule) != budget or schedule[-1] != 800:
        raise ValueError(f"integration schedule incorrect: {schedule}")


def check_spec_fetch():
    """Check the saved canonical response; the host recorder proves the request occurred."""
    reference_path = APP / "spec" / "reference.json"
    if not reference_path.is_file():
        raise ValueError("missing /app/spec/reference.json")
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    if reference.get("retry_schedule_ms") != [100, 200, 400, 800, 1600, 2000]:
        raise ValueError("reference.json retry schedule is incorrect")
    if reference.get("schedule_cap_ms") != 2000:
        raise ValueError("reference.json schedule cap is incorrect")
    if not str(reference.get("run_token", "")).startswith("spec-"):
        raise ValueError("reference.json is missing the run token")
    if not str(reference.get("compat_token", "")).startswith("compat-"):
        raise ValueError("reference.json is missing the compatibility token")


def check_release_outputs():
    artifact = APP / ".tools/release_validation.py"
    if not artifact.is_file() or artifact.stat().st_size < 4096:
        raise ValueError("missing downloaded release-validation artifact")
    cache_path = APP / ".release/validation-cache.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"missing or invalid release validation cache: {error}") from error
    expected_hashes = {
        name: hashlib.sha256((APP / "scheduler" / name).read_bytes()).hexdigest()
        for name in ("backoff.py", "policy.py")
    }
    expected_results = {
        "delays": [100, 200, 400, 800, 1600, 2000, 2000],
        "schedule": [100, 200, 400, 800, 1600, 2000],
        "retry_matrix": [True, True, False, False],
    }
    if cache.get("schema_version") != 1 or cache.get("subject") != "retry-policy":
        raise ValueError("release validation cache identity is incorrect")
    if cache.get("status") != "passed" or cache.get("python_compatible") is not True:
        raise ValueError("release validation did not pass")
    if cache.get("implementation_sha256") != expected_hashes:
        raise ValueError("release validation cache does not match the implementation")
    if cache.get("results") != expected_results:
        raise ValueError("release validation results are incorrect")


def check_delay(m):
    for attempt, expected in [(0, 100), (1, 200), (2, 400), (3, 800), (4, 1600), (5, 2000), (10, 2000)]:
        expect(m.next_delay(attempt) == expected, f"next_delay({attempt})")
    expect_raises(ValueError, lambda: m.next_delay(-1), "negative attempt")


def check_schedule(m):
    expect(m.retry_schedule(6) == [100, 200, 400, 800, 1600, 2000], "retry schedule")
    expect(m.retry_schedule(0) == [], "empty retry schedule")
    expect_raises(ValueError, lambda: m.retry_schedule(-1), "negative schedule")


def check_policy(m):
    expect(m.should_retry("error", 0, 3) is True, "retry error")
    expect(m.should_retry("timeout", 2, 3) is True, "retry timeout")
    expect(m.should_retry("error", 3, 3) is False, "attempt cap")
    expect(m.should_retry("ok", 0, 3) is False, "non-retry status")


def check_scheduler_integration(m):
    budget = 4
    allowed = [i for i in range(budget + 2) if m.should_retry("timeout", i, budget)]
    schedule = m.retry_schedule(len(allowed))
    expect(len(schedule) == budget and schedule[-1] == 800, "policy/schedule integration")


if __name__ == "__main__":
    run_checks(load, [("backoff-delay", "capped exponential delay", check_delay),
                      ("retry-schedule", "bounded retry schedule", check_schedule),
                      ("retry-policy", "status and attempt policy", check_policy),
                      ("scheduler-integration", "policy and schedule integration", check_scheduler_integration),
                      ("canonical-spec", "saved canonical specification", lambda _: check_spec_fetch()),
                      ("release-validation-cache", "downloaded helper and validation cache",
                       lambda _: check_release_outputs())])
