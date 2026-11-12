"""Speed bench: time per image by groups and codes read within 60 / 100 / 500 ms.

    python harness/speed.py prepare --acc <accuracy results> --data <datasets> --dir <out> [--n 150] [--seed 1]
    python harness/speed.py run --dir <out> [--rounds 3] [--mask 0x4] [--python-cv4 <python>] [--sr-dir <dir>]
    python harness/speed.py report --dir <out>

prepare — groups by the accuracy run (bench.py output): for each image with a
truth, which engines read it (unir, zxing-cpp, ZBar, OpenCV with or without
the model):
  clear      — all four;        medium   — unir and at least one rival, not all;
  hard       — unir only;       rival-only — a rival, not unir;
  none       — nobody;          negative — the negative sets (no code).
Up to n images per group (seed). Every image is written as PGM (EXIF
orientation applied, greyscale): all readers get the same bytes and JPEG
decoding is not timed.

run — rounds; in each, unir (Python package libscanner_unir: one code without a
limit and with budget_ms = 500, 100, 60) and then the rivals, each in its own
process pinned to one core (Windows: --mask), single-threaded, images
preloaded, only the read call is timed. Run on an idle machine.

report — per group and reader: median and 90th percentile of the time (minimum
over rounds); read without a limit and within B. unir within B is a run with
budget_ms = B, counted only if it really kept the limit (the limit is soft);
rivals cannot be given a limit, so a code counts if read within <= B ms.

Raw files: raw/r<k>-<reader>.tsv. For unir: mode (codes:budget), idx, ms,
timedOut, codes; for rivals: idx, ms, codes.
"""
import argparse
import csv
import ctypes
import random
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench  # noqa: E402
from codes import canon  # noqa: E402

POS = ['artelab-1', 'artelab-2', 'deal', 'deal-e8', 'smartengines', 'off', 'commons-c128']
NEG = ['negative-deal', 'negative-synth']
RIVALS = ['zxing', 'zbar', 'opencv', 'opencv-sr']
GROUPS = ['clear', 'medium', 'hard', 'rival-only', 'none', 'negative']
UNIR_MODES = [(1, 0), (1, 500), (1, 100), (1, 60)]
BUDGETS = [60, 100, 500]


def read_tsv(p):
    with open(p, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def prepare(a):
    from PIL import Image, ImageOps
    acc, out = Path(a.acc), Path(a.dir)
    (out / 'img').mkdir(parents=True, exist_ok=True)
    pool = defaultdict(list)
    for s in POS + NEG:
        if not (acc / f'{s}-unir.tsv').exists():
            print(f'{s}: not in {acc} — skipped')
            continue
        per = {rd: {r['file']: r for r in read_tsv(acc / f'{s}-{rd}.tsv')} for rd in ['unir'] + RIVALS}
        for f, r in per['unir'].items():
            if s in NEG:
                pool['negative'].append((s, f, ''))
                continue
            if not r['truth']:
                continue
            ok = {rd: int(per[rd][f]['correct']) > 0 for rd in per}
            riv = [ok['zxing'], ok['zbar'], ok['opencv'] or ok['opencv-sr']]
            g = ('clear' if all(riv) else 'medium' if any(riv) else 'hard') if ok['unir'] else \
                ('rival-only' if any(riv) else 'none')
            pool[g].append((s, f, r['truth']))
    rng = random.Random(a.seed)
    rows = []
    for g in GROUPS:
        items = sorted(pool[g])
        pick = sorted(rng.sample(items, min(a.n, len(items))))
        print(f'{g}: {len(items)} images, taken {len(pick)}')
        for s, f, truth in pick:
            k = len(rows)
            im = ImageOps.exif_transpose(Image.open(Path(a.data) / f)).convert('L')
            dst = out / 'img' / f'{k:04d}.pgm'
            im.save(dst)
            rows.append({'idx': k, 'group': g, 'set': s, 'src': f, 'truth': truth, 'w': im.size[0], 'h': im.size[1]})
    with open(out / 'manifest.tsv', 'w', encoding='utf-8', newline='') as o:
        w = csv.DictWriter(o, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def pin(mask):
    if sys.platform == 'win32':
        k = ctypes.windll.kernel32
        k.SetProcessAffinityMask(k.GetCurrentProcess(), ctypes.c_size_t(mask))
    else:
        import os
        os.sched_setaffinity(0, {i for i in range(64) if mask >> i & 1})


def images(d):
    from PIL import Image
    ims = []
    for r in read_tsv(Path(d) / 'manifest.tsv'):
        im = Image.open(Path(d) / 'img' / f'{int(r["idx"]):04d}.pgm')
        im.load()
        ims.append(im)
    return ims


def unir_worker(a):
    """unir through its Python package, in process, like the rivals."""
    import numpy as np
    import unir
    pin(int(a.mask, 0))
    ims = images(a.dir)
    arrs = [np.ascontiguousarray(np.asarray(im, dtype=np.uint8)) for im in ims]
    views = [unir.ImageView(x, x.shape[1], x.shape[0], x.shape[1], unir.PixelFormat.GRAY8) for x in arrs]
    with open(a.out, 'w', encoding='utf-8', newline='') as o:
        o.write('mode\tidx\tms\ttimedOut\tcodes\n')
        for codes, budget in UNIR_MODES:
            s = unir.Settings.single()
            s.symbologies = unir.Symbology.EAN_UPC | unir.Symbology.CODE128 | unir.Symbology.GS1_128
            s.max_codes = codes
            s.budget_ms = float(budget)
            s.timeout_ms = 0.0
            with unir.Scanner(s) as sc:
                for v in views[:5]:   # warm-up
                    sc.scan(v)
                for i, v in enumerate(views):
                    t0 = time.perf_counter()
                    r = sc.scan(v)
                    ms = (time.perf_counter() - t0) * 1000
                    txt = '|'.join(c.text.decode('latin-1').replace('\x1d', '<GS>') for c in r.codes)
                    o.write(f'{codes}:{budget}\t{i}\t{ms:.4f}\t{int(r.timed_out)}\t{txt}\n')


def rival_worker(a):
    pin(int(a.mask, 0))
    bench._init_reader(a.worker, a.sr_dir)
    rd = bench._R
    ims = images(a.dir)
    for im in ims[:5]:
        rd(im)
    with open(a.out, 'w', encoding='utf-8', newline='') as o:
        o.write('idx\tms\tcodes\n')
        for i, im in enumerate(ims):
            t0 = time.perf_counter()
            res = rd(im)
            ms = (time.perf_counter() - t0) * 1000
            codes = '|'.join(dict.fromkeys(r[1].replace('\t', ' ').replace('|', ' ') for r in res))
            o.write(f'{i}\t{ms:.3f}\t{codes}\n')


def run(a):
    d = Path(a.dir)
    (d / 'raw').mkdir(exist_ok=True)
    for r in range(a.rounds):
        for rd in ['unir'] + RIVALS:
            t0 = time.time()
            py = a.python_cv4 if rd == 'opencv-sr' else sys.executable
            subprocess.run([py, '-I', __file__, 'worker', '--worker', rd, '--dir', str(d),
                            '--out', str(d / 'raw' / f'r{r}-{rd}.tsv'), '--mask', a.mask, '--sr-dir', a.sr_dir],
                           check=True)
            print(f'round {r + 1}/{a.rounds}: {rd} {time.time() - t0:.0f} s', flush=True)


def hit(codes, truth):
    if not truth:
        return False
    ts = [canon(t) for t in truth.split('|')]
    return any(canon(c) & t for c in codes.split('|') if c for t in ts)


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * (len(xs) - 1) + 0.5))] if xs else float('nan')


def report(a):
    d = Path(a.dir)
    man = read_tsv(d / 'manifest.tsv')
    rounds = sorted({p.name.split('-')[0] for p in (d / 'raw').glob('r*-unir.tsv')})
    us = defaultdict(lambda: defaultdict(list))   # mode -> idx -> [(ms, codes)] by rounds
    for r in rounds:
        for row in read_tsv(d / 'raw' / f'{r}-unir.tsv'):
            us[row['mode']][int(row['idx'])].append((float(row['ms']), row['codes']))
    rv = {rd: defaultdict(list) for rd in RIVALS}
    for rd in RIVALS:
        for r in rounds:
            p = d / 'raw' / f'{r}-{rd}.tsv'
            if p.exists():
                for row in read_tsv(p):
                    rv[rd][int(row['idx'])].append((float(row['ms']), row['codes']))

    def best(lst):
        return min(m for m, _ in lst), lst[0][1]

    L = [f'# 1D speed by image groups ({len(rounds)} rounds, one thread, one core)', '',
         'Time is the read call only, the image is already in memory (PGM, greyscale); minimum over rounds. '
         'unir looks for one code (early exit); "within B" for unir is a run with budget_ms = B, counted only '
         'if it kept the limit; for rivals — read within <= B ms.', '']
    names = {'clear': 'clear (all read)', 'medium': 'medium (unir and some rivals)', 'hard': 'hard (unir only)',
             'rival-only': 'rivals only', 'none': 'nobody', 'negative': 'no code'}
    for g in GROUPS:
        idx = [int(r['idx']) for r in man if r['group'] == g]
        if not idx:
            continue
        mp = statistics.median(int(man[i]['w']) * int(man[i]['h']) / 1e6 for i in idx)
        sets = defaultdict(int)
        for i in idx:
            sets[man[i]['set']] += 1
        L += [f'## {names[g]} — {len(idx)} images, median {mp:.1f} MP', '',
              'Sets: ' + ', '.join(f'{k} {v}' for k, v in sorted(sets.items(), key=lambda x: -x[1])), '']
        neg = g == 'negative'
        head = '| Reader | median, ms | p90, ms | ' + ('codes returned (false)' if neg else
                                                       'read without limit | ' + ' | '.join(f'within {b} ms' for b in BUDGETS)) + ' |'
        L += [head, '|' + '---|' * (head.count('|') - 1)]

        def line(name, ms, ok_all, ok_b, nfalse):
            cells = [name, f'{statistics.median(ms):.0f}', f'{q(ms, 0.9):.0f}']
            cells += [str(nfalse)] if neg else [str(ok_all)] + [str(ok_b[b]) for b in BUDGETS]
            L.append('| ' + ' | '.join(cells) + ' |')

        ms, ok_all, nfalse = [], 0, 0
        for i in idx:
            m, c = best(us['1:0'][i])
            ms.append(m)
            ok_all += hit(c, man[i]['truth'])
            nfalse += bool(c) if neg else 0
        ok_b = {}
        for b in BUDGETS:
            per_round = [sum(us[f'1:{b}'][i][k][0] <= b and hit(us[f'1:{b}'][i][k][1], man[i]['truth']) for i in idx)
                         for k in range(len(rounds))]
            med = statistics.median(per_round)
            ok_b[b] = f'{med:.0f}' + (f' ({min(per_round)}–{max(per_round)})' if min(per_round) != max(per_round) else '')
        line('**unir**, one code', ms, ok_all, ok_b, nfalse)
        for rd in RIVALS:
            if not rv[rd]:
                continue
            ms, ok_all, nfalse, ok_b = [], 0, 0, {b: 0 for b in BUDGETS}
            for i in idx:
                m, c = best(rv[rd][i])
                ms.append(m)
                h = hit(c, man[i]['truth'])
                ok_all += h
                nfalse += bool(c) if neg else 0
                for b in BUDGETS:
                    ok_b[b] += h and m <= b
            line(rd, ms, ok_all, ok_b, nfalse)
        over = [max(us[f'1:{b}'][i][k][0] for k in range(len(rounds))) - b for b in BUDGETS for i in idx]
        L += ['', f'unir limit: largest overrun {max(over):.0f} ms.', '']
    (d / 'speed.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print(d / 'speed.md')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['prepare', 'run', 'report', 'worker'])
    ap.add_argument('--acc')
    ap.add_argument('--data', default=str(bench.REPO / 'data'))
    ap.add_argument('--dir')
    ap.add_argument('--n', type=int, default=150)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--mask', default='0x4')
    ap.add_argument('--python-cv4', default=sys.executable)
    ap.add_argument('--sr-dir', default=str(bench.REPO / 'wechat_sr'))
    ap.add_argument('--worker')
    ap.add_argument('--out')
    a = ap.parse_args()
    if a.cmd == 'worker':
        (unir_worker if a.worker == 'unir' else rival_worker)(a)
    else:
        {'prepare': prepare, 'run': run, 'report': report}[a.cmd](a)


if __name__ == '__main__':
    main()
