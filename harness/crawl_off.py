"""How the Open Food Facts set was collected (for reference; to get the same images use fetch_lists.py).

    python harness/crawl_off.py <folder> [products=800] [images_per_product=4] [country]

Products come from the daily change dumps (data/delta: the search API is
sometimes unavailable for hours), shuffled; country is a tag like
en:russia, empty — the whole world. For each product with a valid EAN/UPC
code up to N original (numbered) photos are taken, downscaled to 1920 px on
the longer side and written as <folder>/<code>_<n>.jpg plus meta.csv
(file;code;url). Photos smaller than 800 px are skipped: the barcode on them
is smaller than a module per pixel. The truth is the product's code from the
database. Many product photos show no barcode at all (front side,
ingredients), so of the 1258 photos crawled on 2026-10-22 the bench set
(lists/off.csv) keeps the 145 where at least one of two readers — an early
version of our engine or zxing-cpp — read the product code. The selection
favours these two readers; ZBar and OpenCV took no part in it.

Images are CC BY-SA, the database is ODbL (openfoodfacts.org). The crawler
is polite: own User-Agent, 3 download threads.
"""
import csv
import gzip
import io
import json
import random
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

UA = 'barcode-1d-benchmark/1.0 (+https://github.com/libscanner/barcode-1d-benchmark)'
IMG = 'https://images.openfoodfacts.org/images/products/'
DELTA = 'https://static.openfoodfacts.org/data/delta/'


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def folder(code):
    # 13 digits and longer — 3/3/3/rest; shorter — as is (OFF layout)
    if len(code) <= 8:
        return code
    code = code.zfill(13) if len(code) < 13 else code
    return f'{code[:3]}/{code[3:6]}/{code[6:9]}/{code[9:]}'


def fetch_one(code, k):
    url = f'{IMG}{folder(code)}/{k}.jpg'
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(get(url, timeout=90)))).convert('RGB')
    except Exception:
        return None
    if max(im.size) < 800:
        return None
    im.thumbnail((1920, 1920))
    return f'{code}_{k}.jpg', url, im


def delta_pages(rng, country):
    names = [l.strip() for l in get(DELTA + 'index.txt').decode().splitlines() if l.strip().endswith('.json.gz')]
    for name in names:
        prods = []
        for line in gzip.decompress(get(DELTA + name, timeout=600)).splitlines():
            try:
                p = json.loads(line)
            except ValueError:
                continue
            if country and country not in (p.get('countries_tags') or []):
                continue
            prods.append({'code': p.get('code', ''), 'images': p.get('images') or {}})
        rng.shuffle(prods)
        for i in range(0, len(prods), 50):
            yield prods[i:i + 50]


def valid_code(code):
    if not code.isdigit() or len(code) not in (8, 12, 13):
        return False
    d = [int(c) for c in code]
    s = sum(v * (3 if i % 2 == 0 else 1) for i, v in enumerate(reversed(d[:-1])))
    return (10 - s % 10) % 10 == d[-1]


def main(out, products=800, per=4, country=''):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / 'meta.csv'
    have = set()
    if meta_path.exists():
        have = {r['file'] for r in csv.DictReader(open(meta_path, encoding='utf-8'), delimiter=';')}
    new_meta = not meta_path.exists()
    with open(meta_path, 'a', encoding='utf-8', newline='') as meta:
        w = csv.writer(meta, delimiter=';')
        if new_meta:
            w.writerow(['file', 'code', 'url'])
        rng = random.Random()
        pool = ThreadPoolExecutor(3)
        seen, got_products = set(), 0
        for page in delta_pages(rng, country):
            if got_products >= products:
                break
            jobs = []
            for p in page:
                code = str(p.get('code', ''))
                if code in seen or not valid_code(code):
                    continue
                seen.add(code)
                imgs = p.get('images') or {}
                raw = [k for k in (imgs.get('uploaded') or imgs) if str(k).isdigit()]
                jobs += [(code, k) for k in rng.sample(raw, min(per, len(raw))) if f'{code}_{k}.jpg' not in have]
            codes = set()
            for res in pool.map(lambda j: fetch_one(*j), jobs):
                if res is None:
                    continue
                name, url, im = res
                im.save(out / name, quality=90)
                w.writerow([name, name.split('_')[0], url])
                have.add(name)
                codes.add(name.split('_')[0])
            got_products += len(codes)
            print(f'products {got_products}, images {len(have)}', flush=True)


if __name__ == '__main__':
    a = sys.argv
    main(a[1], int(a[2]) if len(a) > 2 else 800, int(a[3]) if len(a) > 3 else 4, a[4] if len(a) > 4 else '')
