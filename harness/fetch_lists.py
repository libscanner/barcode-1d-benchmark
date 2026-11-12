"""Download the Open Food Facts and Wikimedia Commons images of the bench by the lists in lists/.

    python harness/fetch_lists.py [--data data] [--sets off,commons]

Open Food Facts: the original (numbered) product photo, downscaled to 1920 px
on the longer side (as crawl_off.py did) -> data/off/<code>_<n>.jpg.
Wikimedia Commons: the 1920 px wide copy served by the Commons API (as
crawl_commons.py did) -> data/commons/commons_<n>.jpg.

The images keep their licences: OFF photos — CC BY-SA (openfoodfacts.org),
Commons — the licence of each file (column `license` of lists/commons.csv).
If a source re-encoded a file since our crawl, a few borderline images may
read differently.
"""
import argparse
import csv
import io
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = 'barcode-1d-benchmark/1.0 (+https://github.com/libscanner/barcode-1d-benchmark)'
REPO = Path(__file__).resolve().parent.parent


def get(url, timeout=90):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_off(out):
    from PIL import Image, ImageOps
    out.mkdir(parents=True, exist_ok=True)
    for r in csv.DictReader(open(REPO / 'lists/off.csv', encoding='utf-8'), delimiter=';'):
        dst = out / r['file']
        if dst.exists():
            continue
        try:
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(get(r['url'])))).convert('RGB')
        except Exception as e:
            print('skipped', r['file'], e)
            continue
        im.thumbnail((1920, 1920))
        im.save(dst, quality=90)
        print(r['file'], flush=True)


def fetch_commons(out):
    out.mkdir(parents=True, exist_ok=True)
    api = 'https://commons.wikimedia.org/w/api.php'
    for r in csv.DictReader(open(REPO / 'lists/commons.csv', encoding='utf-8'), delimiter=';'):
        dst = out / r['file']
        if dst.exists():
            continue
        q = {'action': 'query', 'titles': r['title'], 'prop': 'imageinfo', 'iiprop': 'url', 'iiurlwidth': 1920,
             'format': 'json'}
        try:
            p = next(iter(json.loads(get(api + '?' + urllib.parse.urlencode(q)))['query']['pages'].values()))
            ii = p['imageinfo'][0]
            dst.write_bytes(get(ii.get('thumburl') or ii['url']))
        except Exception as e:
            print('skipped', r['file'], e)
            continue
        print(r['file'], flush=True)
        time.sleep(0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(REPO / 'data'))
    ap.add_argument('--sets', default='off,commons')
    a = ap.parse_args()
    sets = a.sets.split(',')
    if 'off' in sets:
        fetch_off(Path(a.data) / 'off')
    if 'commons' in sets:
        fetch_commons(Path(a.data) / 'commons')


if __name__ == '__main__':
    main()
