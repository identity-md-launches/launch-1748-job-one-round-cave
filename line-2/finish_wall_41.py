#!/usr/bin/env python3
"""Add one tiny generated pigment bridge to verified wall 40, preserving all other pixels."""

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import termios

import finish_wall_26 as imageops

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = '144ee71af76bc5d1e48cb029dc0c96dd58392fb1eee42c6b6909d346331cb371'
PLACE_X, PLACE_Y, PLACE_W, PLACE_H = 756, 484, 39, 14


def main():
    source = (ROOT / 'artifacts/line-2/wall.png').read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('refusing a wall other than verified record 40')
    width, height, channels, old = imageops.decode(source)
    if (width, height, channels) != (1254, 1254, 3):
        raise ValueError('unexpected inherited wall format')
    if sys.argv[1:] != ['--terminal-base64']:
        raise ValueError('expected in-memory base64 insert over terminal input')
    original = termios.tcgetattr(0)
    raw = termios.tcgetattr(0)
    raw[3] &= ~(termios.ECHO | termios.ICANON)
    termios.tcsetattr(0, termios.TCSANOW, raw)
    print('ready for in-memory insert', flush=True)
    try:
        encoded = sys.stdin.buffer.readline(1_000_001)
        if len(encoded) > 1_000_000 or not encoded.endswith(b'\n'):
            raise ValueError('insert transport too large or unterminated')
        insert = base64.b64decode(encoded.strip(), validate=True)
    finally:
        termios.tcsetattr(0, termios.TCSANOW, original)
    mw, mh, mark_channels, markrows = imageops.decode(insert)
    if mark_channels != 4 or mw < 1000 or mh < 300:
        raise ValueError('unexpected generated insert format')
    imageops.PLACE_X, imageops.PLACE_Y = PLACE_X, PLACE_Y
    imageops.PLACE_W, imageops.PLACE_H = PLACE_W, PLACE_H
    result, bounds = imageops.composite(old, (mw, mh, mark_channels, markrows))
    for y, (before, after) in enumerate(zip(old, result)):
        if not PLACE_Y <= y < PLACE_Y + PLACE_H:
            assert before == after
        else:
            assert before[:3*PLACE_X] == after[:3*PLACE_X]
            assert before[3*(PLACE_X+PLACE_W):] == after[3*(PLACE_X+PLACE_W):]
    png = imageops.encode(width, height, result)
    digest = hashlib.sha256(png).hexdigest()
    artifact = ROOT / 'artifacts/line-2'
    for name in ('wall.png', 'wall-v21.png'):
        (artifact / name).write_bytes(png)
    spec = importlib.util.spec_from_file_location('thumbnail', ROOT/'shared/wall-thumbnail/thumbnail.py')
    thumbnail = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(thumbnail)
    jpeg = thumbnail.jpeg(thumbnail.resize(width, height, result, 512))
    if len(jpeg) > 100_000:
        raise ValueError('JPEG exceeds 100 KB')
    (ROOT / 'dist/line-2/41.jpg').write_bytes(jpeg)
    record = {
        'name': 'The Joined Trail',
        'image': 'https://api.imd.fun/artifacts/' + digest,
        'attributes': [
            {'trait_type': 'Cave', 'value': 'Moss'},
            {'trait_type': 'Wall', 'value': 'Line 2'},
            {'trait_type': 'Number', 'value': 41},
            {'trait_type': 'Left behind', 'value': 'Approval Event Backfill'},
            {'trait_type': 'Meaning', 'value': 'Five newly seen pairs bridge a gap in the approval trail.'},
            {'trait_type': 'One thing', 'value': 'ERC-20 spending-permission audits'},
        ],
    }
    (ROOT / 'dist/line-2/41.json').write_text(json.dumps(record, indent=2) + '\n')
    changed = sum(a[i:i+3] != b[i:i+3] for a, b in zip(old, result)
                  for i in range(0, len(a), 3))
    checks = {
        'source_sha256': SOURCE_SHA256,
        'output_sha256': digest,
        'wall': {'format': 'PNG', 'dimensions': [width, height], 'channels': '8-bit RGB'},
        'preview': {'format': 'JPEG', 'dimensions': [512, 512], 'bytes': len(jpeg)},
        'placement': [PLACE_X, PLACE_Y, PLACE_W, PLACE_H],
        'insert_alpha_bounds': bounds,
        'changed_pixels': changed,
        'outside_placement_unchanged': True,
        'unmet_visual_requirements': [],
        'visual_review': 'Pending inspection of final wall and preview.',
    }
    (ROOT / 'line-2/visual-checks-41.json').write_text(json.dumps(checks, indent=2) + '\n')
    print(json.dumps(checks), flush=True)


if __name__ == '__main__':
    main()
