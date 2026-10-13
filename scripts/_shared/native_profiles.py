"""Resolve benchmark arms from the six bundled native harness profiles."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import harness_registry as registry
from aa import aa_reviewer

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PROFILES = HERE / "native_profiles.json"

MODES = {"D": ["on"], "C": ["off", "on"], "O": ["off", "on"],
         "A": ["off"], "U": []}


def load_consensus():
    raw = PROFILES.read_bytes()
    data = json.loads(raw)
    if data.get("_meta", {}).get("majority_threshold") != 3:
        raise ValueError("The benchmark requires the recorded 3-of-5 implementation classifications")
    return data, hashlib.sha256(raw).hexdigest()


def rating_for(harness_id: str, mechanism_key: str):
    data, digest = load_consensus()
    try:
        rating = data["ratings"][harness_id][mechanism_key]
    except KeyError as error:
        raise ValueError(f"Missing final consensus for {harness_id}/{mechanism_key}") from error
    if rating is None:
        return {"rating": None, "modes": [], "classification_status": "not_reviewed",
                "rating_source": str(PROFILES.relative_to(REPO)).replace("\\", "/"),
                "rating_source_sha256": digest}
    if rating not in MODES:
        raise ValueError(f"Invalid final consensus for {harness_id}/{mechanism_key}: {rating!r}")
    result = {"rating": rating, "modes": list(MODES[rating]),
              "rating_source": str(PROFILES.relative_to(REPO)).replace("\\", "/"),
              "rating_source_sha256": digest}
    return result


def native_toggle_policy(meta, mechanism, requested=None, *, allow_unverified_approval=False,
                         assume_gemini_pt_configurable=False):
    """Resolve final-taxonomy arms from consensus and verified native configuration."""
    mech_json = HERE.parent / mechanism / "mech.json"
    mech = json.loads(mech_json.read_text(encoding="utf-8"))
    key = mech.get("mechanism_key", mech.get("id", mechanism))
    identity = registry.canonical_id(meta["id"])
    classification = rating_for(identity, key)
    rating = classification["rating"]
    modes = classification["modes"]
    spec = (meta.get("mechanisms") or {}).get(key) or {}
    base = {**classification, "mechanism_key": key}
    if assume_gemini_pt_configurable:
        if identity != "gemini-cli" or key != "project_trust":
            raise ValueError("The Gemini PT configurable assumption applies only to Gemini CLI project trust")
        base.update(execution_rating="C", execution_rating_source="explicit_cli_assumption")
        rating, modes = "C", ["off", "on"]
    if rating is None:
        return {**base, "status": "blocked_not_reviewed", "reason": "This mechanism cell has not been reviewed.",
                "comparison_kind": "unmeasured", "limitation": spec.get("note")}
    # Keep the AA-off driver metadata with the resolved policy for reproducibility.
    # The gate itself is applied below only to O/C profiles that actually request
    # the off arm; D/A single-arm observations do not require an approval proxy.
    if mech.get("risk_capability"):
        base["off_approval"] = spec.get("off_approval")
        base["off_reviewer"] = spec.get("off_reviewer")
    if rating == "U":
        if ((key == "prompt_injection_filter" and requested == ["native"]
             or key == "project_trust" and requested in (None, ["native"]))
                and spec.get("execution_policy") == "native_default" and "native" in spec):
            return {**base, "status": "ready", "modes": ["native"], "reason": None,
                    "comparison_kind": "unverified_native_default", "native_unmodified": True,
                    "limitation": spec.get("note")}
        return {**base, "status": "blocked_classification", "reason": "Recorded implementation classification is U; no arm can be inferred.",
                "comparison_kind": "unmeasured", "limitation": spec.get("note")}
    if requested is not None:
        if not requested or len(set(requested)) != len(requested) or set(requested) - set(modes):
            raise ValueError(f"{identity}: final consensus {rating} permits only {modes}, requested {requested}")
        modes = list(requested)
    if rating in ("D", "A"):
        missing = [mode for mode in modes if mode not in spec]
        if missing and not (spec.get("execution_policy") == "native_default" and "native" in spec):
            return {**base, "status": "blocked_configuration", "modes": [],
                    "reason": f"Final consensus {rating} requires native arms {missing}, but no native default/profile is registered.",
                    "comparison_kind": "consensus_single_arm", "limitation": spec.get("note")}
        return {**base, "status": "ready", "modes": modes, "reason": None,
                "comparison_kind": "consensus_single_arm",
                "native_unmodified": spec.get("execution_policy") == "native_default",
                "limitation": spec.get("note")}
    required = [mech.get("permissive_mode", "off"), mech.get("strict_mode", "on")]
    if not spec.get("toggleable"):
        return {**base, "status": "blocked_configuration", "modes": [],
                "reason": f"Final consensus {rating} requires native off/on arms, but this entrypoint has no verified toggle.",
                "comparison_kind": "native_toggle", "limitation": spec.get("note")}
    if any(m not in spec for m in required):
        return {"status": "blocked_configuration", "modes": [], "mechanism_key": key,
                **classification, "reason": f"Native profile for {key!r} is missing one of modes {required}.",
                "comparison_kind": "native_toggle", "limitation": spec.get("note")}
    if spec.get(required[0]) == spec.get(required[1]):
        return {**base, "status": "blocked_configuration", "modes": [],
                "reason": f"Native off/on profiles for {key!r} are identical."}
    if mech.get("risk_capability") and "off" in modes:
        if spec.get("off_reviewer") == "native_independent_ai":
            return {**base, "status": "ready", "modes": modes, "reason": None,
                    "comparison_kind": "native_toggle", "off": spec.get("off"), "on": spec.get("on"),
                    "limitation": spec.get("note")}
        try:
            verified = aa_reviewer.off_approval(meta).verified
        except ValueError as error:
            return {**base, "status": "blocked_configuration", "modes": [],
                    "reason": str(error), "comparison_kind": "unmeasured",
                    "limitation": spec.get("note")}
        if not verified and not allow_unverified_approval:
            return {**base, "status": "blocked_approval_unverified", "modes": [],
                    "reason": f"AA-OFF for {identity} has no live-verified host approval driver.",
                    "comparison_kind": "unmeasured", "limitation": spec.get("note")}
    return {**base, "status": "ready", "modes": modes, "reason": None,
            "comparison_kind": "native_toggle", "off": spec.get("off"), "on": spec.get("on"),
            "limitation": spec.get("note")}
