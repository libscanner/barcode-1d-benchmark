"""Summary of the sheet frames: python multi_sum.py [results dir] > results/summary.md

Truth: every frame shows one A4 sheet of 20 codes (sheets/truth.json); the codes of the two sheets do not overlap.
The sheet of a frame is found by the codes any reader read. Correct = a code of that sheet; foreign = any other text."""
import collections
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
O = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'results')
READERS = [('unir', 'unir 1.2.18'), ('scandit', 'Scandit 8.7.1'), ('zxing', 'zxing-cpp 3.1.1'),
           ('zbar', 'ZBar 0.23.93'), ('opencv', 'OpenCV 5.1'), ('unir4', 'unir 1.2.18, 4 threads')]
KIND = {'sheet-ean13': 'EAN-13', 'sheet-sscc': 'SSCC (GS1-128)'}


def norm(t):
    return t.replace('<GS>', '').replace('\x1d', '').replace(' ', '').replace('(', '').replace(')', '')


T = json.load(open(os.path.join(HERE, 'sheets', 'truth.json'), encoding='utf-8'))
sheet_of = {norm(c['text']): s for s, v in T.items() for c in v}


def load(p):
    r = {}
    for line in open(p, encoding='utf-8', errors='replace'):
        f = line.rstrip('\n').split('\t')
        if len(f) >= 4:
            r[f[0]] = (float(f[1]), {norm(c) for c in f[2].split('\x1f') if norm(c)}, float(f[3]))
    return r


def q90(v):
    return v[int(0.9 * len(v))]


D = {k: load(f'{O}/{k}.tsv') for k, _ in READERS if os.path.exists(f'{O}/{k}.tsv')}
frames = sorted(set.intersection(*[set(d) for d in D.values()]))
sheet = {}
for f in frames:
    c = collections.Counter(sheet_of[x] for d in D.values() for x in d[f][1] if x in sheet_of)
    sheet[f] = c.most_common(1)[0][0] if c else None
kinds = [k for k in KIND if k in set(sheet.values())]
nfr = collections.Counter(sheet[f] for f in frames)
good = {k: {f: {x for x in D[k][f][1] if sheet_of.get(x) == sheet[f]} for f in frames} for k in D}
L = [f'# {len(frames)} frames: ' + ', '.join(f'{KIND[k]} sheet {nfr[k]}' for k in kinds) +
     f'; frames nobody read anything on: {nfr[None]}', '',
     'One core, unir in one thread (except the "4 threads" row); barcodes only; time = the read call only.', '']
hdr = '| reader | correct | of 20 × frames | whole sheets | foreign | ' + \
      ' | '.join(KIND[k] for k in kinds) + ' | median, ms | p90, ms | CPU / wall |'
L += [hdr, '|' + '---|' * (hdr.count('|') - 1)]
tot = 20 * sum(nfr[k] for k in kinds)
for k, title in READERS:
    if k not in D:
        continue
    ok = sum(len(good[k][f]) for f in frames)
    bad = sum(len(D[k][f][1] - good[k][f]) for f in frames)
    full = sum(len(good[k][f]) == 20 for f in frames)
    byk = collections.Counter()
    for f in frames:
        byk[sheet[f]] += len(good[k][f])
    ms = sorted(D[k][f][0] for f in frames)
    cpu = sum(D[k][f][2] for f in frames) / max(1e-9, sum(ms))
    L.append(f'| {title} | {ok} | {100 * ok / tot:.1f} % | {full} | {bad} | ' +
             ' | '.join(f'{byk[s]} ({100 * byk[s] / max(1, 20 * nfr[s]):.1f} %)' for s in kinds) +
             f' | {statistics.median(ms):.0f} | {q90(ms):.0f} | {cpu:.2f} |')
L += ['', '## Time by sheet, median / p90, ms', '', '| reader | ' + ' | '.join(KIND[k] for k in kinds) + ' |',
      '|---|' + '---|' * len(kinds)]
for k, title in READERS:
    if k in D:
        cells = []
        for s in kinds:
            v = sorted(D[k][f][0] for f in frames if sheet[f] == s) or [0]
            cells.append(f'{statistics.median(v):.0f} / {q90(v):.0f}')
        L.append(f'| {title} | ' + ' | '.join(cells) + ' |')
if 'unir' in D:
    L += ['', '## Only unir / only the other reader (codes)', '']
    for k, title in READERS[1:5]:
        if k in D:
            ou = sum(len(good['unir'][f] - good[k][f]) for f in frames)
            ot = sum(len(good[k][f] - good['unir'][f]) for f in frames)
            L.append(f'- {title}: only unir {ou}, only {title.split()[0]} {ot}')
    union = sum(len(set().union(*(good[k][f] for k in D))) for f in frames)
    L.append(f'- read by any reader: {union}; by none: {tot - union}')
L += ['', '## Frames by codes of the sheet read (0–5 / 6–10 / 11–15 / 16–19 / 20)', '']
for k, title in READERS:
    if k in D:
        b = collections.Counter()
        for f in frames:
            n = len(good[k][f])
            b[0 if n <= 5 else 1 if n <= 10 else 2 if n <= 15 else 3 if n < 20 else 4] += 1
        L.append(f'- {title}: ' + ' / '.join(str(b[i]) for i in range(5)))
sys.stdout.reconfigure(encoding='utf-8')
print('\n'.join(L))
