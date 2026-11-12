"""How truth/*.csv were derived from the authors' markup (the files are already in the repository).

    python harness/prepare_truth.py [--data data] [--out truth-check] artelab deal smartengines

  artelab      — BarcodeDatasets/Dataset{1,2}/<image>.txt (EAN-13): Dataset1 —
                 phone with autofocus (artelab-1), Dataset2 — without (artelab-2);
  deal         — DEAL KAIST (Zenodo 13586402): barcode_bb (rec + single_test)
                 and e8_bb — the code is at the start of the file name (13 or
                 8 digits) and must have a valid check digit; background —
                 the negative set (negative-deal);
  smartengines — markup/*.json: type and value without the check digit (added
                 for EAN/UPC); only images whose symbols are all EAN-13,
                 UPC-A, UPC-E or CODE-128 are kept — images of other
                 symbologies are not in the set; the bench takes a random
                 3000 of them (seed 1, bench.py --sample).

Open Food Facts, Wikimedia Commons and the synthetic negatives have no
authors' markup: see crawl_off.py, crawl_commons.py and negative_synth.py.
Paths in the output are relative to the set folder (bench.py SETS).
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codes import ean_check, upce_to_upca  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
IMG = re.compile(r'\.(jpe?g|png|bmp|tiff?)$', re.I)


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as o:
        o.write('file;code;symbology\n')
        for r in rows:
            o.write(';'.join(r) + '\n')
    print(f'{path}: images {len(rows)}, with truth {sum(1 for r in rows if r[1])}')


def artelab(data, out):
    for k in (1, 2):
        d = data / 'artelab' / 'BarcodeDatasets' / f'Dataset{k}'
        rows = []
        for p in sorted(d.iterdir()):
            if not IMG.search(p.name):
                continue
            t = d / (p.name + '.txt')
            code = re.sub(r'\D', '', t.read_text(encoding='latin-1')) if t.exists() else ''
            if code and (len(code) != 13 or ean_check(code[:12]) != code[12]):
                print(f'  Dataset{k}/{p.name}: markup {code} is not an EAN-13 with a valid check digit (kept as is)')
            rows.append((p.name, code, 'EAN-13'))
        write(out / f'artelab-{k}.csv', rows)


def by_name(root, sub):
    """The code is at the start of the file name (digits up to the first non-digit)."""
    rows = []
    for p in sorted(x for x in (root / sub).rglob('*') if IMG.search(x.name)):
        m = re.match(r'(\d+)', p.name)
        code = (m.group(1) if m else '')[:13]
        ok = len(code) in (8, 12, 13) and ean_check(code[:-1]) == code[-1]
        upce = len(code) == 8 and code[0] in '01' and ean_check(upce_to_upca(code)[:-1]) == code[-1]
        if not (ok or upce):
            code = ''
        sym = 'UPC-E' if upce and code else {13: 'EAN-13', 12: 'UPC-A', 8: 'EAN-8'}.get(len(code), '')
        rows.append((p.relative_to(root).as_posix(), code, sym))
    return rows


def deal(data, out):
    root = data / 'deal'
    write(out / 'deal.csv', by_name(root, 'barcode_bb'))
    write(out / 'deal-e8.csv', by_name(root, 'e8_bb'))
    write(out / 'negative-deal.csv', [(p.relative_to(root).as_posix(), '', '')
                                      for p in sorted(x for x in (root / 'background').rglob('*') if IMG.search(x.name))])


KEEP = {'EAN-13': 'EAN-13', 'EAN13': 'EAN-13', 'UPC-A': 'UPC-A', 'UPCA': 'UPC-A', 'UPC-E': 'UPC-E', 'UPCE': 'UPC-E',
        'CODE-128': 'CODE-128', 'CODE128': 'CODE-128'}


def smartengines(data, out):
    d = data / 'smartengines'
    # image img_1.png_0.png_0.png... (one suffix per augmentation) <-> markup img_1.png_0.png.json
    imgs = {}
    for p in d.rglob('*.png'):
        m = re.match(r'(img_\d+\.png_\d+\.png)', p.name)
        if m and p.parent.parent.name == 'images':
            imgs[m.group(1)] = p
    rows, kinds = [], defaultdict(int)
    for js in sorted(d.rglob('*.json')):
        if js.parent.parent.name != 'markup' or js.stem not in imgs:
            continue
        m = json.loads(js.read_text(encoding='utf-8'))
        items = m if isinstance(m, list) else m.get('barcodes', m.get('objects', [m]))
        codes, syms, other = [], set(), False
        for it in items:
            ty = str(it.get('type') or it.get('symbology') or it.get('barcode_type') or '').upper()
            val = str(it.get('value') or it.get('message') or it.get('code') or '')
            kinds[ty] += 1
            s = KEEP.get(ty)
            if not s:
                other = True
                continue
            if s == 'EAN-13' and len(val) == 12:
                val += ean_check(val)
            elif s == 'UPC-A' and len(val) == 11:
                val += ean_check(val)
            elif s == 'UPC-E' and len(val) in (6, 7):   # 6 digits — number system 0
                val = val.zfill(7)
                val += ean_check(upce_to_upca(val + '0')[:-1])
            codes.append(val)
            syms.add(s)
        if other or not codes:   # an image of another symbology — not in the set
            continue
        rows.append((imgs[js.stem].relative_to(d).as_posix(), '|'.join(codes), '|'.join(sorted(syms))))
    write(out / 'smartengines.csv', rows)
    print('  markup symbologies:', dict(kinds))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sets', nargs='+', choices=['artelab', 'deal', 'smartengines'])
    ap.add_argument('--data', default=str(REPO / 'data'))
    ap.add_argument('--out', default=str(REPO / 'truth-check'))
    a = ap.parse_args()
    for s in a.sets:
        globals()[s](Path(a.data), Path(a.out))


if __name__ == '__main__':
    main()
