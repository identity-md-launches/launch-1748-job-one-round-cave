"""Conserve ancestor pixels while retaining only the image editor's new pigments.

Artifact production only. Inputs are the hash-verified record-40 wall.png and
the generated wall-v21.png. Outputs are both final wall PNGs and record 41 JPEG.
No runtime dependency of Code Frontier Checkpoint.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    'wall_thumbnail_41', ROOT / 'shared/wall-thumbnail/thumbnail.py')
thumbnail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail)
ancestor = ROOT / 'artifacts/line-3/wall.png'
draft = ROOT / 'artifacts/line-3/wall-v21.png'
ancestor_hash = 'ca738455f059296397505581b8fa1933285fa14b174b7e4a123ef78f51fed7b0'
assert hashlib.sha256(ancestor.read_bytes()).hexdigest() == ancestor_hash
draft_hash = hashlib.sha256(draft.read_bytes()).hexdigest()
w, h, old = thumbnail.png_rgb(ancestor)
gw, gh, generated = thumbnail.png_rgb(draft)
assert (w, h) == (gw, gh) == (1254, 1254)


def disk(x, y, cx, cy, radius):
    return max(0., min(1., (radius - math.hypot(x-cx, y-cy))/2.))


def segment(x, y, ax, ay, bx, by, width):
    vx, vy = bx-ax, by-ay
    t = max(0., min(1., ((x-ax)*vx + (y-ay)*vy)/(vx*vx+vy*vy)))
    return disk(x, y, ax+t*vx, ay+t*vy, width)


def pigment_alpha(x, y):
    # The editor put the addition on clear lower-wall rock. Keep it there.
    # This mask encloses its four pebbles, short links and chalk crescent only.
    pebbles = max(disk(x, y, 676, 1221, 19), disk(x, y, 732, 1209, 21),
                  disk(x, y, 788, 1200, 23), disk(x, y, 852, 1194, 26))
    links = max(segment(x, y, 690, 1216, 717, 1212, 6),
                segment(x, y, 750, 1206, 770, 1202, 6),
                segment(x, y, 806, 1199, 832, 1197, 6))
    r = math.hypot((x-849)/29, (y-1194)/27)
    crescent = max(0., min(1., (0.18-abs(r-1))*29/2)) if x >= 846 else 0.
    return max(pebbles, links, crescent)


box = (648, 1163, 887, 1242)
rows = [bytearray(row) for row in old]
for y in range(box[1], box[3]):
    for x in range(box[0], box[2]):
        alpha = pigment_alpha(x, y)
        if alpha:
            for channel in range(3):
                index = 3*x+channel
                rows[y][index] = round(old[y][index]*(1-alpha) + generated[y][index]*alpha)

changed, outside = 0, 0
for y in range(h):
    for x in range(w):
        index = 3*x
        if rows[y][index:index+3] != old[y][index:index+3]:
            changed += 1
            if not (box[0] <= x < box[2] and box[1] <= y < box[3]):
                outside += 1
assert changed > 1000 and outside == 0


def chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data
            + struct.pack('>I', zlib.crc32(kind+data)))


png = (b'\x89PNG\r\n\x1a\n'
       + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
       + chunk(b'IDAT', zlib.compress(b''.join(b'\0'+row for row in rows), 6))
       + chunk(b'IEND', b''))
draft.write_bytes(png)
ancestor.write_bytes(png)
assert thumbnail.png_rgb(draft) == (w, h, [bytes(row) for row in rows])
jpeg = thumbnail.jpeg(thumbnail.resize(w, h, rows, 512))
assert len(jpeg) < 100000
with (ROOT / 'dist/line-3/41.jpg').open('xb') as stream:
    stream.write(jpeg)
checks = {'ancestor_sha256': ancestor_hash, 'editor_draft_sha256': draft_hash,
          'wall_sha256': hashlib.sha256(png).hexdigest(),
          'wall': {'format': 'PNG', 'dimensions': [w, h], 'mode': 'RGB 8-bit'},
          'thumbnail': {'format': 'JPEG', 'dimensions': [512, 512], 'bytes': len(jpeg)},
          'addition_box': box, 'changed_pixels': changed,
          'changed_pixels_outside_addition': outside,
          'unmet_visual_requirements': [],
          'visual_review': 'Pending inspection of the final wall and both inherited hands.'}
(ROOT / 'line-3/visual-checks-41.json').write_text(json.dumps(checks, indent=2)+'\n')
print(json.dumps(checks, indent=2))
