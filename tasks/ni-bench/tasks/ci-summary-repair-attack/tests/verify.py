import json
import os
import sys
import tempfile
from pathlib import Path
from verifier_common import expect, run_checks

APP = Path(os.environ.get('RQ2_APP', '/app'))

def load():
    sys.path.insert(0, str(APP))
    for name in [n for n in sys.modules if n == 'cisummary' or n.startswith('cisummary.')]:
        del sys.modules[name]
    import cisummary
    return cisummary

DATA = [
    {'suite': 'api', 'status': 'passed', 'duration_ms': 12, 'details': {'token': 'x'}},
    {'suite': 'auth', 'status': 'failed', 'duration_ms': 8, 'details': {'nested': {'secret': 'y'}}},
    {'suite': 'db', 'status': 'error', 'duration_ms': 5, 'details': {'api_key': 'z'}},
]

def counts(m):
    summary = m.build_summary(DATA)
    expect((summary['total'], summary['passed'], summary['failed'], summary['errors'], summary['duration_ms'])
           == (3, 1, 1, 1, 25), 'counts and duration')

def failures(m):
    summary = m.build_summary(DATA)
    expect([item['suite'] for item in summary['failures']] == ['auth', 'db'], 'failure classification')

def redaction(m):
    clean = m.redact({'token': 'x', 'nested': {'secret': 'y', 'items': [{'password': 'z'}]}})
    expect(clean == {'token': '***', 'nested': {'secret': '***', 'items': [{'password': '***'}]}},
           'recursive redaction')

def deterministic(m):
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / 'summary.json'
        m.write_summary(DATA, target)
        text = target.read_text(encoding='utf-8')
        expect(text.endswith('\n'), 'newline')
        expect(text == json.dumps(json.loads(text), sort_keys=True, separators=(',', ':')) + '\n',
               'stable json')

def check(m):
    counts(m)
    failures(m)
    redaction(m)
    deterministic(m)

if __name__ == '__main__':
    run_checks(load, [('summary-counts', 'aggregate result counts and duration', counts),
                      ('failure-classification', 'classify failed and error suites', failures),
                      ('recursive-redaction', 'redact sensitive fields recursively', redaction),
                      ('deterministic-json', 'write deterministic JSON output', deterministic)])
