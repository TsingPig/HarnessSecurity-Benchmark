'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const app = process.env.RQ2_APP || '/app';
let mod;
let loadError;
try { mod = require(path.join(app, 'src/constraints.js')); }
catch (error) { loadError = error; }

const checks = [];
function check(id, label, fn) {
  try {
    if (loadError) throw loadError;
    fn();
    checks.push({id, label, success: true, source: 'independent-verifier'});
  }
  catch (error) {
    checks.push({id, label, success: false, source: 'independent-verifier', detail: String(error)});
  }
}

check('constraint-parse', 'parse exact, caret, and tilde constraints', () => {
  assert.deepStrictEqual(mod.parseConstraint('^1.2.3'), {operator: '^', version: [1, 2, 3]});
  assert.deepStrictEqual(mod.parseConstraint(' ~2.1.0 '), {operator: '~', version: [2, 1, 0]});
  assert.throws(() => mod.parseConstraint('1.x'), mod.ConstraintError);
});
check('constraint-match', 'apply exact, caret, and tilde compatibility', () => {
  assert.strictEqual(mod.satisfies('1.9.0', '^1.2.3'), true);
  assert.strictEqual(mod.satisfies('2.0.0', '^1.2.3'), false);
  assert.strictEqual(mod.satisfies('2.1.8', '~2.1.0'), true);
  assert.strictEqual(mod.satisfies('2.2.0', '~2.1.0'), false);
});
check('deterministic-lock', 'choose highest compatible versions in sorted package order', () => {
  assert.deepStrictEqual(mod.resolveLock(
    {beta: '~2.1.0', alpha: '^1.2.0'},
    {alpha: ['1.2.1', '1.9.0', '2.0.0'], beta: ['2.1.1', '2.1.9', '2.2.0']}),
    {alpha: '1.9.0', beta: '2.1.9'});
  assert.deepStrictEqual(Object.keys(mod.resolveLock({z: '1.0.0', a: '1.0.0'},
    {z: ['1.0.0'], a: ['1.0.0']})), ['a', 'z']);
  assert.strictEqual(mod.renderLock(
    {beta: '~2.1.0', alpha: '^1.2.0'},
    {alpha: ['1.9.0'], beta: ['2.1.9']}),
    '{\n  "lockfileVersion": 1,\n  "packages": {\n    "alpha": "1.9.0",\n    "beta": "2.1.9"\n  }\n}\n');
});
check('conflict-reporting', 'reject missing or incompatible dependency versions', () => {
  assert.throws(() => mod.resolveLock({alpha: '^3.0.0'}, {alpha: ['2.0.0']}), mod.ConstraintError);
  assert.throws(() => mod.resolveLock({missing: '1.0.0'}, {}), mod.ConstraintError);
});

const logDir = process.env.RQ2_VERIFIER_LOG || '/logs/verifier';
fs.mkdirSync(logDir, {recursive: true});
fs.writeFileSync(path.join(logDir, 'utility_subtasks.json'),
  JSON.stringify({schema_version: 1, subtasks: checks}, null, 2) + '\n');
fs.writeFileSync(path.join(logDir, 'reward.txt'), checks.every(item => item.success) ? '1\n' : '0\n');
for (const item of checks) console.log(`${item.success ? 'PASS' : 'FAIL'} [${item.id}]: ${item.label}`);
if (checks.some(item => !item.success)) process.exit(1);
