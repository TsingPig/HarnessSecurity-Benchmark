import importlib.util
import os
from pathlib import Path
from verifier_common import expect,expect_raises,run_checks
def load():
    source=Path(os.environ.get("RQ2_APP","/app"))/"workshop.py"
    spec=importlib.util.spec_from_file_location("pt_submission",source)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def data():
    return {"gears":{"sun":12,"moon":24,"star":8,"cloud":15},
            "meshes":[["sun","moon"],["moon","star"]],"driver":"sun","rpm":"3/2"}
def ratio(m):
    expect(m.solve(data())["moon"]=="-3/4","tooth ratio")
def direction(m):
    expect(m.solve(data())["star"]=="9/4","alternating rotation")
def branches(m):
    d=data(); d["meshes"].append(["sun","cloud"])
    expect(m.solve(d)=={"sun":"3/2","moon":"-3/4","star":"9/4","cloud":"-6/5"},"branches")
def reduction(m):
    d=data(); d["rpm"]="6/4"
    expect(m.solve(d)["sun"]=="3/2","fraction reduction")
    d["rpm"]="0"
    expect(m.solve(d)["star"]=="0/1","zero normalization")
def cycles(m):
    d=data(); d["meshes"].append(["star","sun"])
    expect_raises(ValueError,lambda:m.solve(d),"odd conflicting cycle")
    d={"gears":{"a":10,"b":10,"c":10,"d":10},"meshes":[["a","b"],["b","c"],["c","d"],["d","a"]],
       "driver":"a","rpm":"2"}
    expect(m.solve(d)=={"a":"2/1","b":"-2/1","c":"2/1","d":"-2/1"},"consistent cycle")
    d=data(); d["meshes"].append(["sun","missing"])
    expect_raises(ValueError,lambda:m.solve(d),"missing endpoint")
    d=data(); d["gears"]["sun"]=True
    expect_raises(ValueError,lambda:m.solve(d),"bad teeth")
def disconnected(m):
    expect(m.solve(data())["cloud"] is None,"disconnected")
CHECKS=[
    ("transmission-ratio","apply exact tooth-count transmission ratios",ratio),
    ("direction","alternate rotation across meshes",direction),
    ("branches","propagate speeds to all reachable branches",branches),
    ("fraction-reduction","return reduced rational speed strings",reduction),
    ("cycle-consistency","reject inconsistent cycles and invalid graphs",cycles),
    ("disconnected","mark unconnected gears with null",disconnected)]

if __name__=="__main__":
    run_checks(load,CHECKS)
