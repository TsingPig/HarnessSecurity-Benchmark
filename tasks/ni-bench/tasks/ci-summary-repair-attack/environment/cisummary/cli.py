import json
import sys
from pathlib import Path
from .aggregate import write_summary

def main(argv):
    if len(argv) != 2:
        return 2
    results = json.loads(Path(argv[0]).read_text(encoding='utf-8'))
    write_summary(results, argv[1])
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
