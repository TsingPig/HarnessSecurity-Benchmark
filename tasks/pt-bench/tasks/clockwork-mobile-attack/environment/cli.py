import json
import sys
from pathlib import Path
from workshop import solve
result=solve(json.loads(Path(sys.argv[1]).read_text()))
target=Path(sys.argv[2])
target.write_text(json.dumps(result,indent=2)+"\n")
