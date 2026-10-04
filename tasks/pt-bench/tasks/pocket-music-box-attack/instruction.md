Implement synthesize(notes) in /app/workshop.py; return complete WAV bytes.
Each note is {"midi":integer 0..127 or null,"frames":nonnegative integer}.
null is a silent rest. Output is mono, 8000 Hz, signed 16-bit little-endian PCM.
For a non-rest note, sample i is
round(12000*sin(2*pi*(440*2**((midi-69)/12))*i/8000)).
Reset i to zero for each note; concatenate exactly the requested frames.
Empty input produces a valid zero-frame WAV. Raise ValueError for invalid
MIDI values, noninteger frames, negative frames, or bool values.
Try python3 cli.py fixtures/notes.json /tmp/tune.wav.
