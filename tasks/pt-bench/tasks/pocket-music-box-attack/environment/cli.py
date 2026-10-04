import json
import sys
from pathlib import Path
from workshop import synthesize
result=synthesize(json.loads(Path(sys.argv[1]).read_text()))
target=Path(sys.argv[2])
target.write_bytes(result)
