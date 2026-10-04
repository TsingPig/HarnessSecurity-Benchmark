ALPHABET=".#@"
def encode(rows):
    width=len(rows[0]) if rows else 0
    if any(len(row)!=width or any(c not in ALPHABET for c in row) for row in rows):
        raise ValueError("invalid pixels")
    encoded=[]
    for row in rows:
        runs=[]
        for c in row:
            if runs and runs[-1][0]==c:
                runs[-1][1]+=1
            else:
                runs.append([c,1])
        encoded.append(runs)
    return {"width":width,"height":len(rows),"runs":encoded}
def decode(sprite):
    width,height,encoded=sprite["width"],sprite["height"],sprite["runs"]
    if (type(width) is not int or type(height) is not int or width<0 or height<0
            or len(encoded)!=height or (height==0 and width!=0)):
        raise ValueError("invalid dimensions")
    rows=[]
    for runs in encoded:
        pieces,previous=[],None
        for c,count in runs:
            if (c not in ALPHABET or len(c)!=1 or type(count) is not int
                    or count<=0 or c==previous):
                raise ValueError("invalid run")
            pieces.append(c*count); previous=c
        row="".join(pieces)
        if len(row)!=width:
            raise ValueError("invalid row width")
        rows.append(row)
    return rows
