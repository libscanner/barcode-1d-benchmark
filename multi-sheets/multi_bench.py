"""Sheets of 20 barcodes from an industrial camera: one reader on all frames.

    python multi_bench.py <reader> <frames dir> [unir threads] [frames.lst] > results/<reader>.tsv

Readers: unir, scandit, zxing, zbar, opencv. Every reader gets the same symbologies (EAN-13/UPC-A, EAN-8, UPC-E,
Code 128 and GS1-128) and is not told which sheet is in the frame. The frame is decoded to grayscale in memory
beforehand; the time is the read call only.
Output: frame, ms, texts separated by \x1f, CPU ms (all threads of the process).
Scandit: scanditsdk.py (ctypes binding of the Scandit Linux C API, not included) and your licence key in the file
named by SCANDIT_KEY (default ~/scwork/key.txt)."""
import os
import sys
import time

import numpy as np
from PIL import Image

name, src = sys.argv[1], sys.argv[2]
threads = int(sys.argv[3]) if len(sys.argv) > 3 else 1
files = sorted(f for f in os.listdir(src) if f.endswith('.png'))
if len(sys.argv) > 4:   # frame list (frames.lst)
    keep = {x.strip() for x in open(sys.argv[4], encoding='utf-8') if x.strip()}
    files = [f for f in files if f in keep]


def clean(s):
    return ''.join(' ' if ord(ch) < 32 else ch for ch in s)


if name == 'unir':
    import dataclasses
    import unir
    S = unir.Symbology
    mask = S.CODE128 | S.GS1_128 | S.EAN_UPC
    # UNIR_NET=on|off forces the scout network; unset = Auto (with barcodes only Auto keeps it off)
    net = {'on': True, 'off': False}.get(os.environ.get('UNIR_NET', ''), None)
    sc = unir.Scanner(dataclasses.replace(unir.Settings.multi(64), symbologies=mask, budget_ms=4000.0,
                                          threads=threads, use_net=net))

    def read(a):
        v = unir.ImageView(a, a.shape[1], a.shape[0], a.shape[1], unir.PixelFormat.GRAY8)
        return [c.text.decode('latin-1') for c in sc.scan(v).codes]

elif name == 'scandit':
    import scanditsdk as sd
    key = open(os.path.expanduser(os.environ.get('SCANDIT_KEY', '~/scwork/key.txt')), encoding='utf-8').read().strip()
    work = os.path.expanduser('~/scwork/w')
    os.makedirs(work, exist_ok=True)
    ctx = sd.RecognitionContext(key, work)
    del key
    scanner = sd.BarcodeScanner(ctx)
    st = sd.BarcodeScannerSettings(preset=sd.PRESET_HIGH_EFFORT)
    st.code_location_constraint_1d = sd.CODE_LOCATION_IGNORE
    st.code_location_constraint_2d = sd.CODE_LOCATION_IGNORE
    st.code_direction_hint = sd.CODE_DIRECTION_NONE
    st.max_num_locations_to_process_per_frame = 64
    st.multi_scan_enabled = True
    for s in (sd.SYMBOLOGY_CODE128, sd.SYMBOLOGY_EAN13_UPCA, sd.SYMBOLOGY_EAN8, sd.SYMBOLOGY_UPCE):
        st.enable_symbology(s, True)
        st.symbologies[s].color_inverted_enabled = True
    if not scanner.apply_settings(st).is_success():
        sys.exit('scandit: settings rejected')
    scanner.wait_for_setup_completed()

    def read(a):
        d = sd.ImageDescription()
        d.width, d.height = a.shape[1], a.shape[0]
        d.set_plane_row_bytes(0, a.shape[1])
        d.layout = sd.IMAGE_LAYOUT_GRAY_8U
        d.memory_size = a.size
        seq = ctx.start_new_frame_sequence()
        res = seq.process_frame(d, a.ctypes.data)
        codes = list(scanner.session.newly_recognized_codes) if res.is_success() else []
        seq.end()
        out = []
        for c in codes:
            try:
                out.append(c.data or '')
            except LookupError:
                out.append('')
        return out

elif name == 'zxing':   # as in the article: rotate, downscale, invert, two binarizers
    import zxingcpp as z
    F = z.BarcodeFormat
    fmts = F.EAN13 | F.EAN8 | F.UPCA | F.UPCE | F.Code128

    def read(a):
        out = []
        for b in (z.Binarizer.LocalAverage, z.Binarizer.GlobalHistogram):
            out += [r.text for r in z.read_barcodes(a, formats=fmts, try_rotate=True, try_downscale=True,
                                                    try_invert=True, text_mode=z.TextMode.Plain, binarizer=b)]
        return out

elif name == 'zbar':    # as in the article: frame, inverted, rotated 45°
    from PIL import ImageOps
    from pyzbar import pyzbar
    Z = pyzbar.ZBarSymbol
    syms = [Z.EAN13, Z.EAN8, Z.UPCA, Z.UPCE, Z.CODE128]

    def read(a):
        im = Image.fromarray(a)
        out = []
        for v in (im, ImageOps.invert(im), im.rotate(45, expand=True, fillcolor=255)):
            out += [r.data.decode('latin-1') for r in pyzbar.decode(v, symbols=syms)]
        return out

elif name == 'opencv':  # cv2.barcode without a model (EAN/UPC; OpenCV does not read Code 128)
    import cv2
    bd = cv2.barcode.BarcodeDetector()

    def read(a):
        try:
            ok, info = bd.detectAndDecodeWithType(a)[:2]
        except cv2.error:
            return []
        return [t for t in info if t] if ok else []
else:
    sys.exit('unknown reader ' + name)

sys.stdout.reconfigure(encoding='utf-8')
for f in files:
    try:
        a = np.ascontiguousarray(np.asarray(Image.open(os.path.join(src, f)).convert('L'), dtype=np.uint8))
    except Exception as e:
        print(f'{f}: {e}', file=sys.stderr)
        continue
    t, c = time.perf_counter(), time.process_time()
    texts = read(a)
    ms = (time.perf_counter() - t) * 1000
    cpu = (time.process_time() - c) * 1000
    seen = []
    for x in texts:
        x = clean(x.replace('\x1d', '<GS>'))
        if x and x not in seen:
            seen.append(x)
    print(f'{f}\t{ms:.1f}\t' + '\x1f'.join(seen) + f'\t{cpu:.1f}', flush=True)
sys.stdout.flush()
os._exit(0)   # the Scandit SDK hangs on a normal interpreter exit
