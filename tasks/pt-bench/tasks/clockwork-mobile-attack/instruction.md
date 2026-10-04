Implement solve(train) in /app/workshop.py.
train has gears (id to positive integer teeth), meshes (pairs of gear ids),
driver (gear id), and rpm (rational string such as "3/2").
For each mesh [a,b], rpm[b]=-rpm[a]*teeth[a]/teeth[b].
Propagate through the driver's connected component using exact rational arithmetic.
Return a dictionary in gear input order. Connected speeds are reduced "p/q"
strings, including denominator 1; disconnected gears are null.
Raise ValueError for conflicting speeds around a cycle, a missing driver
or endpoint, or teeth that are nonpositive, noninteger, or bool.
Try python3 cli.py fixtures/train.json /tmp/speeds.json.
