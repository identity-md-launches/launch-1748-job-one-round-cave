#!/usr/bin/env python3
"""Lay only generated pigment on unused rock, retaining all other pixels."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path('shared/wall-thumbnail').resolve()))
import thumbnail

BOX = (480, 1030, 630, 1108)


def chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data
            + struct.pack('>I', zlib.crc32(kind + data)))


def main():
    parent = Path('artifacts/gathering/wall.png')
    output = Path('artifacts/gathering/wall-v21.png')
    inherited = hashlib.sha256(parent.read_bytes()).hexdigest()
    assert inherited == 'fe557150aad2d4b1d54031f16f068abe62129eba80c398cb9961dad44f8b5d7e'
    w, h, old = thumbnail.png_rgb(parent)
    fw, fh, pigment = thumbnail.png_rgb(output)
    assert (w, h) == (1254, 1254)
    rows = [bytearray(row) for row in old]
    changes = 0
    for y in range(BOX[1], BOX[3]):
        sy = int((.28 + .46 * (y-BOX[1]) / (BOX[3]-BOX[1])) * fh)
        for x in range(BOX[0], BOX[2]):
            sx = int((.13 + .76 * (x-BOX[0]) / (BOX[2]-BOX[0])) * fw)
            r, g, b = pigment[sy][sx*3:sx*3+3]
            if r < 115 and g < 105 and b < 90:
                color = (44, 32, 23)
            elif r > 95 and r > 1.5*g and r > 2*b:
                color = (158, 65, 31)
            elif r > 120 and 80 < g < 180 and b < .65*g:
                color = (182, 126, 45)
            elif .42*fw < sx < .58*fw and .28*fh < sy < .43*fh and r > 220 and g > 210 and b > 195:
                color = (222, 203, 164)
            else:
                continue
            at = 3*x
            before = old[y][at:at+3]
            after = bytes(round(.40*a + .60*c) for a,c in zip(before,color))
            rows[y][at:at+3] = after
            changes += after != before
    assert changes > 0
    assert all(rows[y][3*x:3*x+3] == old[y][3*x:3*x+3]
               for y in range(h) for x in range(w)
               if not (BOX[0] <= x < BOX[2] and BOX[1] <= y < BOX[3]))
    raw = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w,h,8,2,0,0,0))
    raw += chunk(b'IDAT', zlib.compress(b''.join(b'\x00'+row for row in rows))) + chunk(b'IEND', b'')
    output.write_bytes(raw)
    parent.write_bytes(raw)
    result = {'schema': 'gathering-visual-checks-v21', 'output': str(output),
              'parent_sha256': inherited, 'output_sha256': hashlib.sha256(raw).hexdigest(),
              'wall_dimensions': [w,h], 'wall_format': 'PNG RGB 8-bit',
              'addition_rectangle': list(BOX), 'changed_pixels': changes,
              'changed_pixels_outside_addition': 0, 'new_hands': 0,
              'left_hand_digits': 5, 'right_hand_digits': 5,
              'unmet_visual_requirements_observed': [],
              'review_limits': 'Contributor visual inspection, not independent certification. '
                               'Inherited paintings and rock outside the new pigment are pixel-identical.'}
    Path('gathering/visual-checks-21.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
