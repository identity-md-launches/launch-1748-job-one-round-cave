#!/usr/bin/env python3
"""Check this round's records, image bytes, gallery, tests and Git write scope."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path('shared/wall-thumbnail').resolve()))
import thumbnail


class Gallery(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections, self.images, self.links, self.headings = [], [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section':
            self.sections.append(attrs.get('id'))
        if tag == 'img':
            self.images.append(attrs['src'])
        if tag == 'a':
            self.links.append(attrs.get('href'))


def jpeg_dimensions(raw):
    assert raw[:2] == b'\xff\xd8' and raw[-2:] == b'\xff\xd9'
    at = 2
    while at < len(raw):
        assert raw[at] == 255
        marker = raw[at+1]
        at += 2
        length = int.from_bytes(raw[at:at+2], 'big')
        if marker == 192:
            assert raw[at+2] == 8
            height, width = struct.unpack('>HH', raw[at+3:at+7])
            return width, height
        at += length
    raise ValueError('no baseline JPEG frame')


def main():
    wall = Path('artifacts/gathering/wall-v21.png')
    width, height, _ = thumbnail.png_rgb(wall)
    assert (width, height) == (1254, 1254)
    raw = wall.read_bytes()
    assert raw[24:26] == bytes([8, 2])
    assert Path('artifacts/gathering/wall.png').read_bytes() == raw
    sha = hashlib.sha256(raw).hexdigest()
    record = json.loads(Path('dist/gathering/21.json').read_text())
    assert set(record) == {'name', 'image', 'attributes'}
    assert record['image'] == 'https://api.imd.fun/artifacts/'+sha
    expected_traits = [('Cave', 'Moss'), ('Wall', 'Gathering'), ('Number', 21),
                       ('Left behind', 'Proof and Gas Budget Context'),
                       ('Meaning', 'Four stones share one bowl only when their evidence fits the same place and time.'),
                       ('One thing', 'Gathering')]
    assert record['attributes'] == [{'trait_type': key, 'value': value}
                                    for key, value in expected_traits]
    assert type(record['attributes'][2]['value']) is int
    jpeg = Path('dist/gathering/21.jpg')
    assert jpeg_dimensions(jpeg.read_bytes()) == (512, 512)
    assert jpeg.stat().st_size < 100_000
    visual = json.loads(Path('gathering/visual-checks-21.json').read_text())
    assert visual['output_sha256'] == sha
    assert visual['changed_pixels'] > 0 and visual['changed_pixels_outside_addition'] == 0
    assert visual['left_hand_digits'] == visual['right_hand_digits'] == 5
    assert visual['unmet_visual_requirements_observed'] == []
    goals = json.loads(Path('dist/goals.json').read_text())
    assert goals == [{'line': n, 'goal': Path(f'line-{n}/GOAL.md').read_text().strip()}
                     for n in range(1,5)]
    slugs = [f'line-{n}' for n in range(1,5)] + ['gathering']
    gallery = Gallery()
    page = Path('dist/index.html').read_text()
    gallery.feed(page)
    assert gallery.sections == slugs
    count, painted, pending = 0, 0, 0
    for slug in slugs:
        records = sorted(Path('dist',slug).glob('[0-9][0-9].json'), reverse=True)
        last_at = -1
        for path in records:
            item = json.loads(path.read_text())
            assert item['image'] in gallery.links
            is_pending = item['name'] == 'Not painted yet'
            count += 1; pending += is_pending; painted += not is_pending
            if not is_pending:
                image = f'{slug}/{int(path.stem):02}.jpg'
                assert image in gallery.images and Path('dist', image).is_file()
                at = page.index('src="'+image+'"')
                assert at > last_at, 'paintings must be newest first'
                last_at = at
    assert len(gallery.images) == count
    assert '<style>' in page and '<script src=' not in page and 'rel="stylesheet"' not in page
    report = Path('gathering/REPORT.md').read_text()
    for n in range(1,5):
        assert f'| {n} —' in report
    assert Path('gathering/COINS.md').read_text().startswith('none\n')
    checks = json.loads(Path('gathering/check-results-21.json').read_text())
    assert checks['all_passed'] and all(c['passed'] for c in checks['checks'])
    for extra_file in ('gathering/latest-demos-21.json', 'gathering/extra-checks-21.json'):
        additional = json.loads(Path(extra_file).read_text())
        assert additional['all_passed'] and all(c['passed'] for c in additional['checks'])
        checks['checks'].extend(additional['checks'])
    assert not subprocess.run(['git', 'diff', '--name-only', 'HEAD', '--', 'line-1', 'line-2', 'line-3', 'line-4'], capture_output=True, text=True, check=True).stdout
    changed = subprocess.run(['git','diff','--name-only','HEAD'],
                             capture_output=True,text=True,check=True).stdout.splitlines()
    untracked = subprocess.run(['git','ls-files','--others','--exclude-standard'],
                               capture_output=True,text=True,check=True).stdout.splitlines()
    allowed = ('gathering/', 'shared/', 'dist/', 'artifacts/gathering/', 'test/scratch/')
    for name in changed + untracked:
        assert name.startswith(allowed), 'out-of-scope write: '+name
        p = Path(name)
        if p.is_file() and not name.startswith(('artifacts/','test/scratch/')):
            assert p.stat().st_size <= 100_000, 'oversize file: '+name
    # Required wall is for the separate uploader, never staged as source.
    tracked = subprocess.run(['git','ls-files','--',str(wall)],
                             capture_output=True,text=True,check=True).stdout
    assert not tracked
    result = {'schema': 'gathering-delivery-checks-v21', 'all_passed': True,
              'wall_sha256': sha, 'wall_dimensions': [width,height],
              'wall_format': 'PNG RGB 8-bit', 'thumbnail_dimensions': [512,512],
              'thumbnail_format': 'baseline JPEG', 'records': count,
              'painted': painted, 'pending': pending, 'goals': len(goals),
              'checked_commands': len(checks['checks']),
              'tests': sum(c.get('test_count',0) for c in checks['checks']),
              'line_folders_modified': False, 'required_wall_untracked': True,
              'unmet_visual_requirements_observed': [],
              'authority': 'Local contributor checks; visual judgments are not independently certified.'}
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
