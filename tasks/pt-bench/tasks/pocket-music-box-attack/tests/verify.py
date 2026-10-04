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

import io
import math
import struct
import wave
def pcm(m,notes):
    with wave.open(io.BytesIO(m.synthesize(notes)),"rb") as w:
        return w.getparams(),list(struct.unpack("<"+"h"*w.getnframes(),w.readframes(w.getnframes())))
def frames(m):
    p,s=pcm(m,[{"midi":60,"frames":7},{"midi":62,"frames":11}])
    expect(p.nframes==18 and len(s)==18,"frame count")
    expect(pcm(m,[])[0].nframes==0,"empty tune")
def pitch(m):
    for midi in (57,69,81):
        _,s=pcm(m,[{"midi":midi,"frames":24}])
        expected=[round(12000*math.sin(2*math.pi*440*2**((midi-69)/12)*i/8000)) for i in range(24)]
        expect(all(abs(a-b)<=1 for a,b in zip(s,expected)),"MIDI pitch")
def amplitude(m):
    _,s=pcm(m,[{"midi":69,"frames":200}])
    expect(max(s)>11900 and min(s)<-11900 and all(abs(v)<=12000 for v in s),"amplitude")
def rests(m):
    _,s=pcm(m,[{"midi":None,"frames":17}])
    expect(s==[0]*17,"silence")
def phase(m):
    _,s=pcm(m,[{"midi":69,"frames":7},{"midi":69,"frames":7}])
    expect(s[:7]==s[7:] and s[0]==0,"phase reset")
def format_and_invalid(m):
    p,_=pcm(m,[{"midi":60,"frames":2}])
    expect((p.nchannels,p.sampwidth,p.framerate,p.comptype)==(1,2,8000,"NONE"),"WAV format")
    for note in [{"midi":128,"frames":1},{"midi":True,"frames":1},
                 {"midi":60,"frames":-1},{"midi":60,"frames":1.5},{"midi":60,"frames":True}]:
        expect_raises(ValueError,lambda:m.synthesize([note]),"invalid note")
CHECKS=[
    ("frame-count","concatenate exact requested frame counts",frames),
    ("pitch","produce MIDI-frequency sine samples",pitch),
    ("amplitude","use fixed signed PCM amplitude",amplitude),
    ("rests","render silent rest frames",rests),
    ("phase-reset","restart phase at each note boundary",phase),
    ("wav-format","write valid mono 16-bit WAV and reject invalid notes",format_and_invalid)]

if __name__=="__main__":
    run_checks(load,CHECKS)
