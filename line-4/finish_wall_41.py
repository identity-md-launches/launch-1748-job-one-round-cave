#!/usr/bin/env python3
"""Conserve the image editor's tiny addition and produce record 41's outputs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path.cwd().resolve()
WALL = ROOT / 'artifacts/line-4/wall.png'
OUTPUT = ROOT / 'artifacts/line-4/wall-v21.png'
THUMB = ROOT / 'dist/line-4/41.jpg'
RECORD = ROOT / 'dist/line-4/41.json'
ANCESTOR = '4065148239bbff31a4c8d6d8569b0f30924e43ba349b117f45fd274551475e3d'
PATCH = (930, 620, 1105, 742)


def near_segment(x, y, a, b, radius):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((x-a[0])*dx + (y-a[1])*dy)/(dx*dx+dy*dy)))
    return (x-a[0]-t*dx)**2 + (y-a[1]-t*dy)**2 <= radius**2


def pigment_region(x, y):
    # Conserve only the editor's scale strokes, bowls and pebbles, not its
    # altered rock. These coordinates mask the generated shapes; they paint none.
    stroke = (948 <= x <= 1080 and 637 <= y <= 653 or
              1003 <= x <= 1024 and 623 <= y <= 734 or
              988 <= x <= 1038 and 723 <= y <= 740)
    for a, b in [((955, 647), (939, 700)), ((955, 647), (979, 700)),
                 ((1070, 647), (1040, 700)), ((1070, 647), (1090, 700))]:
        stroke = stroke or near_segment(x, y, a, b, 4)
    bowl = (935 <= x <= 987 or 1036 <= x <= 1094) and 696 <= y <= 721
    pebble = any((x-cx)**2 + (y-690)**2 <= 9**2 for cx in (960, 1063))
    return stroke, bowl, pebble


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def main():
    assert hashlib.sha256(WALL.read_bytes()).hexdigest() == ANCESTOR
    assert not THUMB.exists() and not RECORD.exists()
    spec = importlib.util.spec_from_file_location('codec41',
        ROOT / 'line-4/tools/call-rehearsal/thumbnail.py')
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    width, height, old = codec.png_rgb(WALL)
    sw, sh, generated = codec.png_rgb(OUTPUT)
    assert (width, height) == (sw, sh) == (1254, 1254)
    generated_hash = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    rows = [bytearray(row) for row in old]
    left, top, right, bottom = PATCH
    for y in range(top, bottom):
        for x in range(left, right):
            i = 3*x
            previous = old[y][i:i+3]
            red, green, blue = generated[y][i:i+3]
            difference = sum(abs(previous[c] - (red, green, blue)[c]) for c in range(3))
            stroke, bowl, pebble = pigment_region(x, y)
            ochre = red > 1.5*green and red-green > 35 and green > blue
            charcoal = red < 100 and green < 75 and blue < 60
            yellow = red > 125 and green > 73 and red > 1.15*green and green > 1.5*blue
            # Select the generated earth pigment, retaining unpainted stone.
            if difference > 70 and (stroke and charcoal or bowl and ochre or pebble and yellow):
                rows[y][i:i+3] = generated[y][i:i+3]
    inside = outside = 0
    for y in range(height):
        for x in range(width):
            i = 3*x
            if rows[y][i:i+3] != old[y][i:i+3]:
                if left <= x < right and top <= y < bottom:
                    inside += 1
                else:
                    outside += 1
    assert inside > 500 and outside == 0
    png = (b'\x89PNG\r\n\x1a\n' +
           chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
           chunk(b'IDAT', zlib.compress(b''.join(b'\0' + bytes(row) for row in rows), 9)) +
           chunk(b'IEND', b''))
    jpeg = codec.jpeg(codec.resize(width, height, rows, 512))
    assert len(jpeg) < 100_000
    OUTPUT.write_bytes(png)
    WALL.write_bytes(png)
    THUMB.write_bytes(jpeg)
    checks = {'ancestor_sha256': ANCESTOR, 'generated_sha256': generated_hash,
              'wall_sha256': hashlib.sha256(png).hexdigest(),
              'wall': {'width': width, 'height': height, 'format': 'PNG',
                       'mode': 'RGB', 'bytes': len(png)},
              'thumbnail': {'width': 512, 'height': 512, 'format': 'JPEG', 'bytes': len(jpeg)},
              'addition_rectangle': list(PATCH), 'changed_pixels_inside': inside,
              'changed_pixels_outside': outside,
              'unmet_visual_requirements': [
                  'Inherited tiny three-pronged trail motifs cannot be certified as five-digit handprints; preserved unchanged.']}
    (ROOT / 'line-4/delivery-checks-41.json').write_text(json.dumps(checks, indent=2) + '\n')
    record = {'name': 'The Weighed Embers',
              'image': 'https://api.imd.fun/artifacts/' + checks['wall_sha256'],
              'attributes': [
                  {'trait_type': 'Cave', 'value': 'Moss'},
                  {'trait_type': 'Wall', 'value': 'Line 4'},
                  {'trait_type': 'Number', 'value': 41},
                  {'trait_type': 'Left behind', 'value': 'Gas Budget'},
                  {'trait_type': 'Meaning', 'value': 'Two ochre bowls weigh measured heat against a chosen reserve.'},
                  {'trait_type': 'One thing', 'value': 'Rehearse Ethereum contract calls before submission'}]}
    RECORD.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
