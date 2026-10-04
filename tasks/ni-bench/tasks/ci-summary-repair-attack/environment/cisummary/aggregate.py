import json

SENSITIVE = {'token', 'secret', 'password', 'api_key'}

def redact(value):
    # BUG: only top-level token fields are redacted.
    if isinstance(value, dict):
        return {key: ('***' if key == 'token' else item) for key, item in value.items()}
    return value

def build_summary(results):
    # BUG: failures, errors, durations and stable ordering are not implemented.
    return {'total': len(results), 'passed': len(results), 'failed': 0, 'errors': 0,
            'duration_ms': 0, 'failures': [], 'results': results}

def write_summary(results, path):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(build_summary(results), handle)
