"""Negative set without codes: striped fabric, blinds, halftone, random bars — what a 1D reader may
"see" an EAN or a Code 128 in.

    python harness/negative_synth.py [folder=data/negative-synth] [images=200] [seed=7]

Kinds (in turn): stripes (sine and square wave, own period and angle), plaid
(two coloured stripe systems), blinds (slats with shading and cords), halftone
(a rotated dot grid, like print), pseudo-bars — random widths of 1-4 modules
across the image (the most dangerous: looks like a symbol, but has neither a
check digit nor structure). Each gets perspective, blur, noise, uneven light,
JPEG. Writes <folder>/neg_NNN_<kind>.jpg and expected.csv without truth; the
published set is 200 images with seed 7 (truth/negative-synth.csv).
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

REPO = Path(__file__).resolve().parent.parent


def grid(w, h, ang):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    a = math.radians(ang)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def stripes(rng, w, h):
    u, _ = grid(w, h, rng.uniform(0, 180))
    per = rng.uniform(3, 40)
    s = np.sin(2 * np.pi * u / per)
    if rng.random() < 0.5:
        s = np.sign(s) * np.abs(s) ** 0.2   # square wave with a soft edge
    return 0.5 + 0.4 * s


def plaid(rng, w, h):
    ang = rng.uniform(0, 90)
    u, v = grid(w, h, ang)
    out = np.zeros((h, w, 3), np.float32)
    for k in range(3):
        pu, pv = rng.uniform(4, 30), rng.uniform(4, 30)
        a = (np.sin(2 * np.pi * u / pu + rng.uniform(0, 6)) > rng.uniform(-0.5, 0.5))
        b = (np.sin(2 * np.pi * v / pv + rng.uniform(0, 6)) > rng.uniform(-0.5, 0.5))
        out[..., k] = 0.25 + 0.25 * a + 0.25 * b + rng.uniform(0, 0.2)
    return out


def blinds(rng, w, h):
    u, v = grid(w, h, rng.choice([0, 90]) + rng.uniform(-8, 8))
    per = rng.uniform(15, 60)
    ph = (v % per) / per
    s = 0.85 - 0.5 * ph ** 2 - 0.35 * (ph > 0.93)   # slat lighter at the top, dark gap
    for _ in range(rng.integers(1, 4)):             # cords across the slats
        c = rng.uniform(0, w)
        s = np.where(np.abs(u - c) < 2, 0.2, s)
    return s


def halftone(rng, w, h):
    u, v = grid(w, h, rng.uniform(0, 90))
    per = rng.uniform(4, 12)
    tone = 0.5 + 0.4 * np.sin(u / rng.uniform(80, 300)) * np.cos(v / rng.uniform(80, 300))
    du, dv = (u % per) / per - 0.5, (v % per) / per - 0.5
    r = np.sqrt(du ** 2 + dv ** 2)
    return np.where(r < 0.55 * np.sqrt(1 - tone), 0.1, 0.9)


def pseudo_bars(rng, w, h):
    u, v = grid(w, h, rng.uniform(-20, 20) + rng.choice([0, 90]))
    X = rng.uniform(1.5, 6)
    widths = rng.integers(1, 5, size=200)
    edges = np.cumsum(widths) * X
    idx = np.searchsorted(edges, u - u.min() + rng.uniform(0, 40))
    bar = (idx % 2 == 0).astype(np.float32)
    # a band of bars, background around it
    vc, vh = rng.uniform(0.3, 0.7) * h, rng.uniform(0.15, 0.5) * h
    inside = np.abs(v - v.mean() + (h / 2 - vc)) < vh
    return np.where(inside, 0.1 + 0.8 * (1 - bar), 0.85)


KINDS = [('stripes', stripes), ('plaid', plaid), ('blinds', blinds), ('halftone', halftone), ('bars', pseudo_bars)]


def finish(rng, a, w, h):
    if a.ndim == 2:
        a = np.repeat(a[..., None], 3, axis=2) * np.array(rng.uniform(0.7, 1.0, 3), np.float32)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    light = 0.6 + 0.4 * np.cos((x / w - rng.uniform(0, 1)) * rng.uniform(0.5, 2)) \
        * np.cos((y / h - rng.uniform(0, 1)) * rng.uniform(0.5, 2))
    a = a * light[..., None] + rng.normal(0, rng.uniform(0.005, 0.05), a.shape)
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    # perspective: corners moved by up to 15 %
    d = [rng.uniform(-0.15, 0.15) * s for s in (w, h, w, h, w, h, w, h)]
    quad = (d[0], d[1], d[2], h + d[3], w + d[4], h + d[5], w + d[6], d[7])
    im = im.transform((w, h), Image.QUAD, quad, Image.BILINEAR, fillcolor=(128, 128, 128))
    r = rng.uniform(0, 2.5)
    if r > 0.3:
        im = im.filter(ImageFilter.GaussianBlur(r))
    return im


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / 'data/negative-synth'
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 7)
    out.mkdir(parents=True, exist_ok=True)
    names = []
    for i in range(n):
        kind, fn = KINDS[i % len(KINDS)]
        w, h = [(1280, 960), (1920, 1080), (1024, 1024), (960, 1280)][rng.integers(0, 4)]
        im = finish(rng, fn(rng, w, h), w, h)
        name = f'neg_{i:03d}_{kind}.jpg'
        im.save(out / name, quality=int(rng.integers(70, 95)))
        names.append(name)
    (out / 'expected.csv').write_text('file;code;symbology\n' + ''.join(f'{x};;\n' for x in names), encoding='utf-8')
    print(f'{out}: {n} images')


if __name__ == '__main__':
    main()
