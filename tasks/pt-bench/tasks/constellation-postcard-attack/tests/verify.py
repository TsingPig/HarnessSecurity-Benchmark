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

import copy
import xml.etree.ElementTree as ET
NS="{http://www.w3.org/2000/svg}"
DATA={"stars":[{"id":"a","x":125,"y":750,"brightness":2,"label":"Fox & <Moon>","color":"gold"},
               {"id":"b","x":875,"y":250,"brightness":0,"label":"Tail","color":"blue"}],
      "links":[["a","b"]],"palette":{"gold":"#e0b040","blue":"#4080d0"}}
def dom(m):
    return ET.fromstring(m.render(copy.deepcopy(DATA)))
def coordinates(m):
    r=dom(m)
    expect(r.attrib["viewBox"]=="0 0 128 128","canvas")
    expect([(float(c.attrib["cx"]),float(c.attrib["cy"])) for c in r.findall(NS+"circle")]
           ==[(16,32),(112,96)],"coordinate mapping and y inversion")
    empty=ET.fromstring(m.render({"stars":[],"links":[],"palette":{}}))
    expect(len(empty)==0,"empty sky")
def radii(m):
    expect([float(c.attrib["r"]) for c in dom(m).findall(NS+"circle")]==[3,1],"brightness")
def links(m):
    lines=dom(m).findall(NS+"line")
    expect(len(lines)==1 and [float(lines[0].attrib[k]) for k in ("x1","y1","x2","y2")]
           ==[16,32,112,96],"link endpoints")
def labels(m):
    labels=dom(m).findall(NS+"text")
    expect([e.text for e in labels]==["Fox & <Moon>","Tail"],"escaped XML")
    expect([(float(e.attrib["x"]),float(e.attrib["y"])) for e in labels]==[(16,32),(112,96)],
           "label coordinates")
def colors(m):
    r=dom(m)
    for kind in ("circle","text"):
        expect([e.attrib["fill"] for e in r.findall(NS+kind)]==["#e0b040","#4080d0"],"palette")
def invalid(m):
    for key,value in [("x",-1),("y",1001),("brightness",-1),("color","missing")]:
        d=copy.deepcopy(DATA); d["stars"][0][key]=value
        expect_raises(ValueError,lambda:m.render(d),"invalid "+key)
    d=copy.deepcopy(DATA); d["links"]=[["a","ghost"]]
    expect_raises(ValueError,lambda:m.render(d),"missing endpoint")
    d=copy.deepcopy(DATA); d["stars"][1]["id"]="a"
    expect_raises(ValueError,lambda:m.render(d),"duplicate id")
CHECKS=[
    ("coordinates","map star coordinates onto the SVG canvas",coordinates),
    ("radii","derive circle radius from brightness",radii),
    ("links","draw specified constellation links",links),
    ("labels","place and XML-escape star labels",labels),
    ("colors","resolve palette colors",colors),
    ("invalid-input","reject invalid star and link data",invalid)]

if __name__=="__main__":
    run_checks(load,CHECKS)
