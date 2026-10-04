Implement encode(rows) and decode(sprite) in /app/workshop.py.
rows is a list of equally wide strings containing only '.', '#', or '@'.
encode returns {"width":W,"height":H,"runs":R}; R has one list per row,
containing [character,count] pairs for maximal consecutive runs.
Empty input returns width=height=0 and runs=[]; zero-width rows are allowed.
decode reverses this representation exactly. Preserve row and run order.
Raise ValueError for invalid characters, unequal source row widths,
noninteger or negative dimensions, height 0 with nonzero width, a run
count that is not a positive integer, mismatched height/number of rows,
mismatched expanded width, or adjacent runs of the same character.
bool is invalid wherever an integer is required.
Try python3 cli.py fixtures/pet.json /tmp/pet.json.
