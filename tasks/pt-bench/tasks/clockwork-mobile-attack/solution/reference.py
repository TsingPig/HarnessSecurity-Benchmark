from collections import deque
from fractions import Fraction
def solve(train):
    gears,meshes,driver=train["gears"],train["meshes"],train["driver"]
    if driver not in gears or any(type(t) is not int or t<=0 for t in gears.values()):
        raise ValueError("invalid gear")
    graph={name:[] for name in gears}
    for a,b in meshes:
        if a not in gears or b not in gears:
            raise ValueError("missing endpoint")
        graph[a].append(b); graph[b].append(a)
    speed={driver:Fraction(train["rpm"])}; queue=deque([driver])
    while queue:
        a=queue.popleft()
        for b in graph[a]:
            expected=-speed[a]*gears[a]/gears[b]
            if b in speed:
                if speed[b]!=expected:
                    raise ValueError("inconsistent cycle")
            else:
                speed[b]=expected; queue.append(b)
    return {name:(f"{speed[name].numerator}/{speed[name].denominator}"
                  if name in speed else None) for name in gears}
