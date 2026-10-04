import io
import math
import struct
import wave
def synthesize(notes):
    samples=[]
    for note in notes:
        midi,frames=note["midi"],note["frames"]
        if (type(frames) is not int or frames<0 or (midi is not None
                and (type(midi) is not int or not 0<=midi<=127))):
            raise ValueError("invalid note")
        if midi is None:
            samples.extend([0]*frames)
        else:
            frequency=440*2**((midi-69)/12)
            samples.extend(round(12000*math.sin(2*math.pi*frequency*i/8000))
                           for i in range(frames))
    output=io.BytesIO()
    with wave.open(output,"wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000)
        wav.writeframes(struct.pack("<"+"h"*len(samples),*samples))
    return output.getvalue()
