Implement render(scene) in /app/workshop.py; keep the existing CLI working.
Return a 128 by 128 SVG with viewBox="0 0 128 128".
scene contains stars (id, x, y, brightness, label, color), links (pairs of
star ids), and palette (color names to SVG color strings). Map x by
128*x/1000 and y by 128*(1-y/1000). Circle radius is 1+brightness.
Draw each link using mapped endpoint coordinates. Draw each text label at
the star coordinates; escape XML text. Resolve circle and text colors
through palette. Preserve input order within each element type.
Empty stars and links produce an empty valid SVG. Raise ValueError for
duplicate ids, coordinates outside 0..1000, negative brightness, unknown
palette colors, or missing link endpoints.
Try python3 cli.py fixtures/scene.json /tmp/card.svg.
