'use strict';

class ConstraintError extends Error {}

function parseConstraint(text) {
  // BUG: only exact versions work; caret/tilde constraints and validation are missing.
  const parts = String(text).trim().split('.').map(Number);
  return { operator: '=', version: parts };
}

function satisfies(version, constraint) {
  const parsed = parseConstraint(constraint);
  return version === parsed.version.join('.');
}

function resolveLock(dependencies, catalog) {
  const lock = {};
  for (const [name, constraint] of Object.entries(dependencies)) {
    const matches = (catalog[name] || []).filter(v => satisfies(v, constraint));
    if (!matches.length) throw new ConstraintError(`no compatible version for ${name}`);
    lock[name] = matches[0];
  }
  return lock;
}

function renderLock(dependencies, catalog) {
  return JSON.stringify({lockfileVersion: 1, packages: resolveLock(dependencies, catalog)}, null, 2) + '\n';
}

module.exports = { ConstraintError, parseConstraint, satisfies, resolveLock, renderLock };
