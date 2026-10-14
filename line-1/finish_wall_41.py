#!/usr/bin/env python3
"""Preserve the inherited wall; lay only one small generated pigment addition."""
import hashlib
import json
from pathlib import Path
import sys

from finish_wall_40 import png, write_rgb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'shared/wall-thumbnail'))
import thumbnail


def main():
    ancestor = ROOT / 'artifacts/line-1/wall.png'
    output = ROOT / 'artifacts/line-1/wall-v21.png'
    w, h, channels, inherited = png(ancestor)
    pw, ph, pc, pigment = png(output)
    assert (w, h, channels) == (1254, 1254, 3) and pc == 4
    rows = [bytearray(row) for row in inherited]
    visible = [(x, y) for y in range(ph) for x in range(pw) if pigment[y][4*x+3] > 24]
    left, right = min(x for x, _ in visible), max(x for x, _ in visible)
    top, bottom = min(y for _, y in visible), max(y for _, y in visible)
    x0, y0, dw, dh = 595, 95, 90, 110
    changed = 0
    for dy in range(dh):
        sy = top + (bottom-top+1)*dy//dh
        for dx in range(dw):
            sx = left + (right-left+1)*dx//dw
            red, green, blue, alpha = pigment[sy][4*sx:4*sx+4]
            if alpha <= 24:
                continue
            # Let the original rock texture show through the new pigment.
            opacity = alpha / 255 * 0.60
            x, y = x0+dx, y0+dy
            previous = inherited[y][3*x:3*x+3]
            value = bytes(round(old*(1-opacity) + paint*opacity)
                          for old, paint in zip(previous, (red, green, blue)))
            rows[y][3*x:3*x+3] = value
            changed += value != previous
    outside = sum(rows[y][3*x:3*x+3] != inherited[y][3*x:3*x+3]
                  for y in range(h) for x in range(w)
                  if not (x0 <= x < x0+dw and y0 <= y < y0+dh))
    assert changed > 0 and outside == 0
    ancestor_hash = hashlib.sha256(ancestor.read_bytes()).hexdigest()
    write_rgb(output, w, h, rows)
    content = output.read_bytes()
    ancestor.write_bytes(content)
    jpeg = thumbnail.jpeg(thumbnail.resize(w, h, rows, 512))
    assert len(jpeg) < 100_000
    target = ROOT / 'dist/line-1/41.jpg'
    with target.open('xb') as handle:
        handle.write(jpeg)
    result = {
        'ancestor_sha256': ancestor_hash,
        'wall': {'paths': ['artifacts/line-1/wall.png', 'artifacts/line-1/wall-v21.png'],
                 'format': 'PNG', 'width': w, 'height': h, 'color': '8-bit RGB',
                 'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)},
        'thumbnail': {'path': 'dist/line-1/41.jpg', 'format': 'JPEG',
                      'width': 512, 'height': 512, 'bytes': len(jpeg)},
        'addition_rectangle_xyxy': [x0, y0, x0+dw, y0+dh],
        'changed_pixels_inside_rectangle': changed,
        'changed_pixels_outside_rectangle': outside,
        'visual_review': 'Pending inspection of the final complete wall and thumbnail.',
        'unmet_visual_requirements': []
    }
    (ROOT / 'line-1/visual-checks-41.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
