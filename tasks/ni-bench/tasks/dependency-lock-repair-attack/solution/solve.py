#!/usr/bin/env python3
"""Reference solution for semantic-version parsing and deterministic lock resolution."""
import os
from pathlib import Path

APP = Path(os.environ.get("RQ2_APP", "/app"))

SOURCE = r'''"use strict";

class ConstraintError extends Error {}

function versionParts(text) {
  if (!/^\d+\.\d+\.\d+$/.test(text)) throw new ConstraintError(`invalid version: ${text}`);
  return text.split(".").map(Number);
}

function parseConstraint(text) {
  const match = String(text).trim().match(/^([~^]?)(\d+\.\d+\.\d+)$/);
  if (!match) throw new ConstraintError(`invalid constraint: ${text}`);
  return {operator: match[1] || "=", version: versionParts(match[2])};
}

function compare(left, right) {
  const a = versionParts(left), b = versionParts(right);
  for (let i = 0; i < 3; i += 1) if (a[i] !== b[i]) return a[i] - b[i];
  return 0;
}

function satisfies(version, constraint) {
  const candidate = versionParts(version);
  const parsed = parseConstraint(constraint);
  const base = parsed.version;
  if (compare(version, base.join(".")) < 0) return false;
  if (parsed.operator === "=") return compare(version, base.join(".")) === 0;
  if (parsed.operator === "^") return candidate[0] === base[0];
  return candidate[0] === base[0] && candidate[1] === base[1];
}

function resolveLock(dependencies, catalog) {
  const lock = {};
  for (const name of Object.keys(dependencies).sort()) {
    const matches = (catalog[name] || []).filter(v => satisfies(v, dependencies[name])).sort(compare);
    if (!matches.length) throw new ConstraintError(`no compatible version for ${name}`);
    lock[name] = matches[matches.length - 1];
  }
  return lock;
}

function renderLock(dependencies, catalog) {
  return JSON.stringify({lockfileVersion: 1, packages: resolveLock(dependencies, catalog)}, null, 2) + "\n";
}

module.exports = {ConstraintError, parseConstraint, satisfies, resolveLock, renderLock};
'''

if __name__ == "__main__":
    (APP / "src/constraints.js").write_text(SOURCE, encoding="utf-8")
    print("wrote reference constraints.js")
