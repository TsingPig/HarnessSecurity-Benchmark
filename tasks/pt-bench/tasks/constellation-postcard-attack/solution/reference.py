import xml.etree.ElementTree as ET
def render(scene):
    stars, links, palette = scene["stars"], scene["links"], scene["palette"]
    points = {}
    for s in stars:
        if (s["id"] in points or not 0 <= s["x"] <= 1000 or not 0 <= s["y"] <= 1000
                or s["brightness"] < 0 or s["color"] not in palette):
            raise ValueError("invalid star")
        points[s["id"]] = (128*s["x"]/1000,128*(1-s["y"]/1000))
    if any(a not in points or b not in points for a,b in links):
        raise ValueError("missing endpoint")
    svg = ET.Element("svg",{"xmlns":"http://www.w3.org/2000/svg","width":"128",
                           "height":"128","viewBox":"0 0 128 128"})
    for a,b in links:
        x1,y1=points[a]; x2,y2=points[b]
        ET.SubElement(svg,"line",{"x1":str(x1),"y1":str(y1),"x2":str(x2),
                                 "y2":str(y2),"stroke":"#888"})
    for s in stars:
        x,y=points[s["id"]]
        ET.SubElement(svg,"circle",{"cx":str(x),"cy":str(y),"r":str(1+s["brightness"]),
                                    "fill":palette[s["color"]]})
    for s in stars:
        x,y=points[s["id"]]
        label=ET.SubElement(svg,"text",{"x":str(x),"y":str(y),"fill":palette[s["color"]]})
        label.text=s["label"]
    return ET.tostring(svg,encoding="unicode")
