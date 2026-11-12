"""Accuracy bench: unir and open 1D readers on public sets with ground truth.

    python harness/bench.py --data <datasets> [--sets a,b] [--readers r,s] [--out <dir>]
        [--unir unir] [--color] [--python-cv4 <python>] [--sr-dir <dir>]
        [--jobs N] [--sample 3000] [--seed 1] [--reuse]

--data    folder with the downloaded sets (layout: SETS below, see README);
--color   pass images to unir in colour (as published; rivals always get
          greyscale — they read luminance anyway);
--reuse   do not run a reader whose <out>/<set>-<reader>.tsv exists, take its
          answers from there (recompute the summary only).

Ground truth: truth/<set>.csv (file;code;symbology[;unsure]; file relative to
the set folder; several codes separated by |; empty code — no truth). A set
without a single truth code is negative: everything returned there is foreign.

Readers:
  unir       — the unir command-line tool (pip install libscanner-unir):
               unir --batch <list> --sym ean,128,gs1 --codes 0 --timeout-ms 0
               --single --corners [--color]: EAN/UPC and any Code 128, all
               codes in the image, no time limit;
  zxing      — zxing-cpp: try_rotate, try_downscale, try_invert, the union of
               the LocalAverage and GlobalHistogram binarizers, EAN/UPC/ISBN
               and Code 128;
  zbar       — pyzbar: the image, the inverted image and the image rotated by
               45° (ZBar scans rows along x and y only), union;
  opencv     — cv2.barcode.BarcodeDetector from OpenCV 5 without a model;
  opencv-sr  — OpenCV 4.10 with the WeChat super-resolution model (in OpenCV 5
               the Caffe-model constructor was removed): run by the Python
               given in --python-cv4, model files sr.prototxt and
               sr.caffemodel in --sr-dir (github.com/WeChatCV/opencv_3rdparty,
               branch wechat_qrcode).

Scoring (harness/codes.py): a symbol is read if the reader returned a code
equal to its truth. A returned code not in the truth is foreign: "confirmed"
if another engine returned it too (most likely a real second code in the
image), "single" otherwise (false-read candidates). opencv and opencv-sr are
one engine. precision = correct / (correct + single foreign).

Output: <out>/<set>-<reader>.tsv (per image), <out>/<set>-only-rival.tsv
(truth read by a rival but not by unir), <out>/aliens.tsv, <out>/summary.md.
"""
import argparse
import csv
import datetime
import os
import random
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codes import canon, family  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
TRUTH = REPO / 'truth'

# set -> folder inside --data that the truth file paths are relative to
SETS = {
    'artelab-1': 'artelab/BarcodeDatasets/Dataset1',
    'artelab-2': 'artelab/BarcodeDatasets/Dataset2',
    'deal': 'deal',            # barcode_bb/...
    'deal-e8': 'deal',         # e8_bb/...
    'smartengines': 'smartengines',
    'off': 'off',
    'commons-c128': 'commons',
    'negative-deal': 'deal',   # background/...
    'negative-synth': 'negative-synth',
}
# sets a random sample is taken from (--sample, --seed)
BIG = {'smartengines'}
READERS = ['unir', 'zxing', 'zbar', 'opencv', 'opencv-sr']

# ---------------------------------------------------------------- sets

UNSURE = {}   # path -> codes confirmed by one source only: neither correct nor foreign


def load_set(name, data, sample=0, seed=1):
    """[(path, [truth...], symbology)] or None when the set is not downloaded."""
    root = Path(data) / SETS[name]
    if not root.exists():
        return None
    rows = []
    with open(TRUTH / f'{name}.csv', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter=';'):
            fp = Path(os.path.abspath(root / r['file'])).as_posix()
            codes = [c.strip() for c in (r.get('code') or '').split('|') if c.strip()]
            UNSURE[fp] = [c.strip() for c in (r.get('unsure') or '').split('|') if c.strip()]
            rows.append((fp, codes, (r.get('symbology') or '').strip()))
    missing = [r[0] for r in rows if not Path(r[0]).exists()]
    if missing:
        print(f'  {name}: {len(missing)} images missing, e.g. {missing[0]}')
    rows = [r for r in rows if Path(r[0]).exists()]
    if sample and name in BIG and len(rows) > sample:
        rows = sorted(random.Random(seed).sample(rows, sample))
    return rows


# ---------------------------------------------------------------- unir

def run_unir(exe, files, workdir, jobs, color):
    """{path: (status, ms, [(code, corners)])}; the list is split between several processes."""
    workdir.mkdir(parents=True, exist_ok=True)
    n = max(1, min(jobs, len(files) // 20 + 1))
    parts = [files[i::n] for i in range(n)]

    def one(k):
        lst = workdir / f'unir-{k}.lst'
        lst.write_text('\n'.join(parts[k]) + '\n', encoding='utf-8')
        # no safeguard timeout: under the bench load a several-codes image can take longer than 10 s
        cmd = [exe, '--batch', str(lst), '--sym', 'ean,128,gs1', '--codes', '0', '--timeout-ms', '0', '--single',
               '--corners'] + (['--color'] if color else [])
        return subprocess.run(cmd, capture_output=True).stdout.decode('utf-8', 'replace')

    res = {f: ('?', '', []) for f in files}
    key = {os.path.normcase(f): f for f in files}
    with ThreadPoolExecutor(n) as pool:
        for out in pool.map(one, range(n)):
            for line in out.split('\n'):
                c = line.rstrip('\r').split('\t')   # path, status, ms, text, symbology, corners
                if len(c) < 3:
                    continue
                f = key.get(os.path.normcase(c[0].replace('\\', '/')))
                if f is None:
                    continue
                st, ms, codes = res[f]
                codes = list(codes)
                if len(c) > 3 and c[3]:
                    codes.append((c[3], c[5] if len(c) > 5 else ''))
                # one line per code; the image status is 0 if at least one code was read
                res[f] = ('0' if '0' in (st, c[1]) else c[1] if st == '?' else st, c[2], codes)
    return res


# ---------------------------------------------------------------- rivals (worker process)

_R = None


def _init_reader(name, sr_dir=''):
    global _R
    if name == 'zxing':
        import zxingcpp as z
        F = z.BarcodeFormat
        fmts = F.EAN13 | F.EAN8 | F.UPCA | F.UPCE | F.ISBN | F.Code128
        bins = [z.Binarizer.LocalAverage, z.Binarizer.GlobalHistogram]

        def rd(im):
            out = []
            for b in bins:
                for r in z.read_barcodes(im, formats=fmts, try_rotate=True, try_downscale=True, try_invert=True,
                                         text_mode=z.TextMode.Plain, binarizer=b):
                    p = r.position
                    pts = ' '.join(f'{a.x},{a.y}' for a in (p.top_left, p.top_right, p.bottom_right, p.bottom_left))
                    out.append((str(r.format).split('.')[-1], r.text, pts))
            return out
        _R = rd
    elif name == 'zbar':
        import math
        from PIL import ImageOps
        from pyzbar import pyzbar
        S = pyzbar.ZBarSymbol
        syms = [S.EAN13, S.EAN8, S.UPCA, S.UPCE, S.ISBN13, S.CODE128]

        def rd(im):
            out = []
            W, H = im.size
            variants = [(0, im), (0, ImageOps.invert(im)), (45, im.rotate(45, expand=True, fillcolor=255))]
            for ang, v in variants:
                a = math.radians(ang)
                cx, cy, cx2, cy2 = W / 2, H / 2, v.size[0] / 2, v.size[1] / 2
                for r in pyzbar.decode(v, symbols=syms):
                    pts = []
                    for (x, y) in r.polygon:   # back to the coordinates of the original image
                        dx, dy = x - cx2, y - cy2
                        pts.append(f'{cx + math.cos(a) * dx - math.sin(a) * dy:.1f},'
                                   f'{cy + math.sin(a) * dx + math.cos(a) * dy:.1f}')
                    out.append((r.type, r.data.decode('latin-1'), ' '.join(pts)))
            return out
        _R = rd
    elif name in ('opencv', 'opencv-sr'):
        import cv2
        import numpy as np
        if name == 'opencv-sr':
            det = cv2.barcode.BarcodeDetector(str(Path(sr_dir) / 'sr.prototxt'), str(Path(sr_dir) / 'sr.caffemodel'))
        else:
            det = cv2.barcode.BarcodeDetector()

        def rd(im):
            ok, info, types, pts = det.detectAndDecodeWithType(np.asarray(im))
            out = []
            if ok:
                for i, (t, ty) in enumerate(zip(info, types)):
                    if t:
                        q = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts[i]) if pts is not None else ''
                        out.append((ty, t, q))
            return out
        _R = rd


def load_gray(f):
    from PIL import Image, ImageOps
    return ImageOps.exif_transpose(Image.open(f)).convert('L')


def _work(args):
    name, f, sr_dir = args
    if _R is None:
        _init_reader(name, sr_dir)
    try:
        res = _R(load_gray(f))
    except Exception as e:   # the image cannot be opened — no answer
        return f, [('ERR', str(e)[:60].replace('\t', ' '), '')]
    seen, out = set(), []
    for r in res:
        if r[1] not in seen:
            seen.add(r[1])
            out.append(r)
    return f, out


def reader_version(name):
    if name == 'zxing':
        from importlib.metadata import version
        return f'zxing-cpp {version("zxing-cpp")} rotate+downscale+invert LocalAverage|GlobalHistogram Plain'
    if name == 'zbar':
        from importlib.metadata import version
        return f'pyzbar {version("pyzbar")} 0+inv+45'
    import cv2
    return f'opencv {cv2.__version__} ' + ('sr-wechat' if name == 'opencv-sr' else 'nosr')


def worker_main(name, lst, out, jobs, sr_dir):
    from multiprocessing import Pool
    files = [l for l in Path(lst).read_text(encoding='utf-8').split('\n') if l]
    with open(out, 'w', encoding='utf-8', newline='') as o:
        o.write('#' + reader_version(name) + '\n')
        with Pool(jobs, initializer=_init_reader, initargs=(name, sr_dir)) as pool:
            for f, res in pool.imap_unordered(_work, [(name, f, sr_dir) for f in files], chunksize=4):
                if not res:
                    o.write(f'{f}\t\t\t\n')
                for sym, text, pts in res:
                    text = text.replace('\x1d', '<GS>').replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
                    o.write(f'{f}\t{sym}\t{text}\t{pts}\n')


def run_rival(name, set_name, files, workdir, a):
    """({path: [(code, corners)]}, version)"""
    py = a.python_cv4 if name == 'opencv-sr' else sys.executable
    ver = subprocess.run([py, '-I', __file__, '--version-of', name], capture_output=True, text=True).stdout.strip()
    lst = workdir / f'{set_name}-{name}.lst'
    part = workdir / f'{set_name}-{name}.part.tsv'
    lst.write_text('\n'.join(files) + '\n', encoding='utf-8')
    t0 = time.time()
    subprocess.run([py, '-I', __file__, '--worker', name, '--list', str(lst), '--out', str(part),
                    '--jobs', str(a.jobs), '--sr-dir', a.sr_dir], check=True)
    print(f'  {name}: {len(files)} images, {time.time() - t0:.0f} s', flush=True)
    got = {}
    for l in part.read_text(encoding='utf-8').split('\n')[1:]:
        c = l.split('\t')
        if len(c) >= 4:
            got.setdefault(c[0], [])
            if c[2] and c[1] != 'ERR':
                got[c[0]].append((c[2], c[3]))
    return {f: got.get(f, []) for f in files}, ver


def reuse(path, files):
    """Answers of a reader from a previous <set>-<reader>.tsv."""
    rows = {r['file']: r for r in csv.DictReader(open(path, encoding='utf-8'), delimiter='\t')}
    return {f: [(c, '') for c in rows[f]['got'].split('|') if c] if f in rows else [] for f in files}, \
        {f: (rows[f]['status'], rows[f]['ms']) if f in rows else ('', '') for f in files}


# ---------------------------------------------------------------- scoring

def engine(rd):
    return 'opencv' if rd.startswith('opencv') else rd


def score(rows, results):
    """per[reader] = metrics; found[reader][path] = (correct truth indices, foreign codes); aliens."""
    readers = list(results)
    found = {rd: {} for rd in readers}
    for f, truth, _ in rows:
        tset = [canon(t) for t in truth]
        for rd in readers:
            ok, alien = set(), []
            for c, _ in results[rd].get(f, []):
                k = canon(c)
                hit = [i for i, t in enumerate(tset) if t & k]
                if hit:
                    ok.update(hit)
                elif any(k & canon(u) for u in UNSURE.get(f, ())):
                    pass
                elif not any(k & canon(x) for x in alien):
                    alien.append(c)
            found[rd][f] = (ok, alien)
    per, aliens = {}, []
    for rd in readers:
        m = defaultdict(int)
        for f, truth, sym in rows:
            ok, alien = found[rd][f]
            m['symbols'] += len(truth)
            m['correct'] += len(ok)
            for i, t in enumerate(truth):
                fam = family(t) if not sym else ('c128' if '128' in sym.lower() else 'ean')
                m[f'symbols_{fam}'] += 1
                m[f'correct_{fam}'] += i in ok
            for x in alien:
                conf = [o for o in readers if engine(o) != engine(rd)
                        and any(canon(x) & canon(y) for y in found[o][f][1])]
                m['alien'] += 1
                m['alien_conf' if conf else 'alien_single'] += 1
                aliens.append((rd, f, x, ','.join(conf), '|'.join(truth)))
        per[rd] = m
    return per, found, aliens


def pct(a, b):
    return f'{100 * a / b:.1f}' if b else '—'


def rel(f, data):
    """Path as written to the output: relative to --data."""
    try:
        return Path(f).relative_to(Path(os.path.abspath(data))).as_posix()
    except ValueError:
        return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(REPO / 'data'))
    ap.add_argument('--sets', default=','.join(SETS))
    ap.add_argument('--readers', default=','.join(READERS))
    ap.add_argument('--out', default=str(REPO / 'results' / datetime.date.today().isoformat()))
    ap.add_argument('--unir', default='unir')
    ap.add_argument('--color', action='store_true')
    ap.add_argument('--python-cv4', default=sys.executable)
    ap.add_argument('--sr-dir', default=str(REPO / 'wechat_sr'))
    ap.add_argument('--jobs', type=int, default=max(2, (os.cpu_count() or 4) - 2))
    ap.add_argument('--sample', type=int, default=3000)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--reuse', action='store_true')
    ap.add_argument('--worker')
    ap.add_argument('--list')
    ap.add_argument('--version-of')
    a = ap.parse_args()
    if a.version_of:
        print(reader_version(a.version_of))
        return
    if a.worker:
        worker_main(a.worker, a.list, a.out, a.jobs, a.sr_dir)
        return
    sys.stdout.reconfigure(encoding='utf-8')
    readers = [r for r in a.readers.split(',') if r]
    out = Path(a.out)
    work = out / 'work'
    work.mkdir(parents=True, exist_ok=True)
    summary, all_aliens, versions = [], [], {}
    for sname in [s for s in a.sets.split(',') if s]:
        rows = load_set(sname, a.data, a.sample, a.seed)
        if rows is None:
            print(f'{sname}: {Path(a.data) / SETS[sname]} not found — skipped')
            continue
        files = [r[0] for r in rows]
        print(f'{sname}: {len(files)} images', flush=True)
        results, status = {}, {}
        for rd in readers:
            prev = out / f'{sname}-{rd}.tsv'
            if a.reuse and prev.exists():
                byrel = {rel(f, a.data): f for f in files}
                got, st = reuse(prev, list(byrel))
                results[rd] = {byrel[k]: v for k, v in got.items()}
                if rd == 'unir':
                    status = {byrel[k]: v for k, v in st.items()}
                versions.setdefault(rd, '(from ' + prev.name + ')')
            elif rd == 'unir':
                t0 = time.time()
                res = run_unir(a.unir, files, work, a.jobs, a.color)
                results['unir'] = {f: v[2] for f, v in res.items()}
                status = {f: (v[0], v[1]) for f, v in res.items()}
                versions['unir'] = subprocess.run([a.unir, '--version'], capture_output=True, text=True).stdout.strip() \
                    + (' --color' if a.color else '')
                print(f'  unir: {time.time() - t0:.0f} s', flush=True)
            else:
                results[rd], versions[rd] = run_rival(rd, sname, files, work, a)
        per, found, aliens = score(rows, results)
        all_aliens += [(sname, r, rel(f, a.data), c, conf, t) for r, f, c, conf, t in aliens]
        for rd in readers:
            with open(out / f'{sname}-{rd}.tsv', 'w', encoding='utf-8', newline='') as o:
                w = csv.writer(o, delimiter='\t', lineterminator='\n')
                w.writerow(['file', 'truth', 'got', 'correct', 'alien', 'status', 'ms'])
                for f, truth, _ in rows:
                    ok, alien = found[rd][f]
                    st, ms = status.get(f, ('', '')) if rd == 'unir' else ('', '')
                    w.writerow([rel(f, a.data), '|'.join(truth), '|'.join(c for c, _ in results[rd][f]), len(ok),
                                '|'.join(alien), st, ms])
        union, only_us, only_riv = 0, 0, []
        for f, truth, _ in rows:
            for i, t in enumerate(truth):
                who = [rd for rd in readers if i in found[rd][f][0]]
                union += bool(who)
                if 'unir' in readers:
                    if who == ['unir']:
                        only_us += 1
                    if who and 'unir' not in who:
                        only_riv.append((rel(f, a.data), t, ','.join(who)))
        with open(out / f'{sname}-only-rival.tsv', 'w', encoding='utf-8', newline='') as o:
            w = csv.writer(o, delimiter='\t', lineterminator='\n')
            w.writerow(['file', 'truth', 'readers'])
            w.writerows(only_riv)
        by = defaultdict(int)
        for _, _, who in only_riv:
            for r in who.split(','):
                by[r] += 1
        summary.append((sname, len(files), per, union, only_us, len(only_riv), dict(by)))
        for rd in readers:
            m = per[rd]
            print(f'  {rd:10} correct {m["correct"]}/{m["symbols"]} ({pct(m["correct"], m["symbols"])} %), '
                  f'foreign {m["alien"]} (single {m["alien_single"]})')
    with open(out / 'aliens.tsv', 'w', encoding='utf-8', newline='') as o:
        w = csv.writer(o, delimiter='\t', lineterminator='\n')
        w.writerow(['set', 'reader', 'file', 'code', 'also_by', 'truth'])
        w.writerows(all_aliens)
    write_summary(out, summary, readers, versions)
    print(f'summary: {out / "summary.md"}')


def write_summary(out, summary, readers, versions):
    L = ['# 1D accuracy bench', '',
         'Share = correct / symbols with truth; precision = correct / (correct + single foreign); foreign = '
         'returned code not in the truth, «single+confirmed» (confirmed — another engine returned it too: most '
         'likely a real second code in the image). On negative sets everything returned is foreign.', '',
         '| Set | images | symbols | ' + ' | '.join(readers) + ' | union | unir only | rivals only |',
         '|---|---|---|' + '---|' * len(readers) + '---|---|---|']
    tot = defaultdict(int)
    for sname, n, per, union, only_us, only_riv, _ in summary:
        sym = per[readers[0]]['symbols']
        cells = []
        for rd in readers:
            m = per[rd]
            tot[rd] += m['correct']
            if sym:
                cells.append(f'{m["correct"]} ({pct(m["correct"], sym)} %), p. '
                             f'{pct(m["correct"], m["correct"] + m["alien_single"])} %, '
                             f'foreign {m["alien_single"]}+{m["alien_conf"]}')
            else:
                cells.append(f'false {m["alien_single"]}+{m["alien_conf"]}')
        tot['symbols'] += sym
        L.append(f'| {sname} | {n} | {sym} | ' + ' | '.join(cells) + f' | {union} | {only_us} | {only_riv} |')
    if tot['symbols']:
        L.append(f'| **total** | | {tot["symbols"]} | ' + ' | '.join(
            f'**{tot[rd]} ({pct(tot[rd], tot["symbols"])} %)**' for rd in readers) + ' | | | |')
    L += ['', '## By symbology', '',
          '| Set | symbology | symbols | ' + ' | '.join(readers) + ' |', '|---|---|---|' + '---|' * len(readers)]
    for sname, n, per, *_ in summary:
        for fam in ('ean', 'c128'):
            s = per[readers[0]].get(f'symbols_{fam}', 0)
            if s:
                L.append(f'| {sname} | {fam} | {s} | ' + ' | '.join(
                    f'{per[rd].get(f"correct_{fam}", 0)} ({pct(per[rd].get(f"correct_{fam}", 0), s)} %)'
                    for rd in readers) + ' |')
    L += ['', '## Read by a rival only (symbols unir did not read)', '']
    for sname, n, per, union, only_us, only_riv, by in summary:
        if only_riv:
            L.append(f'- {sname}: {only_riv} — ' + ', '.join(f'{k} {v}' for k, v in sorted(by.items())))
    L += ['', '## Readers', ''] + [f'- {k}: {v}' for k, v in versions.items()]
    (out / 'summary.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
