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

def dimensions(m):
    d=m.encode(["..@@..",".####."])
    expect((d["width"],d["height"])==(6,2),"dimensions")
def maximal(m):
    expect(m.encode(["@@@..#"])["runs"]==[[["@",3],[".",2],["#",1]]],"maximal runs")
    d={"width":2,"height":1,"runs":[[["@",1],["@",1]]]}
    expect_raises(ValueError,lambda:m.decode(d),"split runs")
def order(m):
    d=m.encode(["@#.","..@"])
    expect(d["runs"]==[[["@",1],["#",1],[".",1]],[[".",2],["@",1]]],"row/run order")
def roundtrip(m):
    for rows in [["..@@..",".####.","@.##.@"],["#"],["",""]]:
        expect(m.decode(m.encode(rows))==rows,"exact roundtrip")
    expect(m.decode({"width":3,"height":1,"runs":[[[".",2],["@",1]]]})==["..@"],"decode input")
def empty(m):
    d={"width":0,"height":0,"runs":[]}
    expect(m.encode([])==d and m.decode(d)==[],"empty convention")
def invalid(m):
    for rows in [["x"],["##","#"]]:
        expect_raises(ValueError,lambda:m.encode(rows),"bad source pixels")
    for d in [{"width":1,"height":1,"runs":[[["#",0]]]},
              {"width":1,"height":1,"runs":[[["#",True]]]},
              {"width":2,"height":1,"runs":[[["#",1]]]},
              {"width":1,"height":2,"runs":[[["#",1]]]},
              {"width":-1,"height":0,"runs":[]}]:
        expect_raises(ValueError,lambda:m.decode(d),"bad compressed form")
CHECKS=[
    ("dimensions","retain image width and height",dimensions),
    ("maximal-runs","encode maximal runs and reject split runs",maximal),
    ("row-order","preserve row and character order",order),
    ("roundtrip","reconstruct exact original pixels",roundtrip),
    ("empty-image","handle empty and zero-width images",empty),
    ("invalid-input","reject invalid pixels and compressed dimensions",invalid)]

if __name__=="__main__":
    run_checks(load,CHECKS)
