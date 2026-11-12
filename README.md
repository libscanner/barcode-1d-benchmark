# 1D barcode readers on public photo sets

[Русская версия](README.ru.md)

An open comparison of linear barcode readers — EAN-13/8, UPC-A/E and Code 128 —
on 6899 symbols from public photo sets whose ground truth was made by other
people, plus 5840 synthetic SSCC (GS1-128) frames of a conveyor camera. The
truth of every image, the answers of every reader for every image, and the
programs that produced them are published here, so every number below can be
checked and extended.

| reader | version |
|---|---|
| **unir** — the linear engine of [Universal Reader](https://github.com/libscanner/universal-reader) (ours) | 1.2.6 |
| [zxing-cpp](https://github.com/zxing-cpp/zxing-cpp) | 3.1.1 (Python binding) |
| [ZBar](https://github.com/mchehab/zbar) | via pyzbar 0.1.9 |
| [OpenCV](https://opencv.org) `barcode::BarcodeDetector` | 5.0.0 |
| the same with the WeChat super-resolution model | OpenCV 4.10.0 |

Commercial SDKs are not included: the licence terms of most of them prohibit
publishing benchmark results without the vendor's consent.

## Results

### Accuracy

Symbols read (share of all symbols with ground truth in the set):

| set | symbols | **unir** | zxing-cpp | ZBar | OpenCV + SR |
|---|---:|---:|---:|---:|---:|
| Artelab №1, autofocus | 214 | **211 (98.6 %)** | 193 (90.2 %) | 200 (93.5 %) | 206 (96.3 %) |
| Artelab №2, no autofocus | 213 | **198 (93.0 %)** | 32 (15.0 %) | 34 (16.0 %) | 89 (41.8 %) |
| DEAL KAIST, EAN-13 | 3200 | **2889 (90.3 %)** | 2369 (74.0 %) | 2385 (74.5 %) | 2244 (70.1 %) |
| DEAL KAIST, EAN-8 and UPC-E | 89 | **84 (94.4 %)** | 79 (88.8 %) | 80 (89.9 %) | 62 (69.7 %) |
| SmartEngines | 3000 | **1417 (47.2 %)** | 892 (29.7 %) | 1030 (34.3 %) | 222 (7.4 %) |
| Open Food Facts * | 145 | **138 (95.2 %)** | 125 (86.2 %) | 120 (82.8 %) | 96 (66.2 %) |
| Wikimedia Commons, Code 128 | 38 | **37 (97.4 %)** | 34 (89.5 %) | 33 (86.8 %) | 0 — no Code 128 |
| **total** | **6899** | **4974 (72.1 %)** | 3724 (54.0 %) | 3882 (56.3 %) | 2919 (42.3 %) |

OpenCV without the model reads 2827. Full table with precision and foreign
codes, by symbology and "read by a rival only":
[results/accuracy-color/summary.md](results/accuracy-color/summary.md).

\* see [Notes](#notes): the Open Food Facts selection favours unir and zxing-cpp.

**False reads.** On 988 published images without a barcode (788 DEAL
backgrounds and 200 synthetic traps: stripes, plaid, blinds, halftone,
random bars) unir, zxing-cpp and ZBar return nothing; OpenCV returns 7. The
same holds on 3243 further frames from production lines that we cannot
publish. On the images with barcodes, the codes a reader returned that
nobody else confirmed ("single foreign"): unir 6, zxing-cpp 56, ZBar 80,
OpenCV + SR 102. All 6 of unir are real second codes in the image, checked by
eye (results/accuracy-color/aliens.tsv).

unir reads the image in colour here (`--color`): it uses colour for one
fallback pass over the blue channel. Read in greyscale it gets 4881 (70.7 %)
instead of 4974 ([results/accuracy-gray](results/accuracy-gray/summary.md));
the rivals read luminance anyway and get the greyscale image.

### Time

Images are grouped by who reads them, 150 random images per group: **clear** —
all four readers read them, **medium** — unir and some rivals, **hard** — unir
only, **rivals only**, **nobody**, **no code**. Every reader gets the same
greyscale bytes already in memory and runs single-threaded in its own process
pinned to one performance core; only the read call is timed; 3 rounds, the
best time per image. unir looks for one code and gets the limit for real
(`budget_ms` = 60, 100, 500); rivals cannot be given a limit, so a code counts
if read within the limit.

Median / 90th percentile without a limit, ms:

| group (median size) | unir | zxing-cpp | ZBar | OpenCV + SR |
|---|---:|---:|---:|---:|
| clear (1.9 MP) | 14 / 145 | 20 / 91 | 171 / 965 | 20 / 45 |
| medium (0.6 MP) | 10 / 132 | 9 / 27 | 71 / 263 | 16 / 44 |
| hard (0.6 MP) | 11 / 194 | 7 / 19 | 67 / 182 | 15 / 45 |
| rivals only (0.4 MP) | 152 / 642 | 5 / 16 | 43 / 152 | 14 / 34 |
| nobody (0.4 MP) | 43 / 275 | 4 / 8 | 38 / 89 | 12 / 28 |
| no code (0.3 MP) | 39 / 201 | 4 / 8 | 40 / 61 | 8 / 10 |

Read of 150 within 60 / 100 / 500 ms:

| group | unir | zxing-cpp | ZBar | OpenCV + SR |
|---|---|---|---|---|
| clear | 139 / 148 / 150 | 131 / 141 / 150 | 23 / 59 / 112 | 149 / 150 / 150 |
| medium | **134 / 141 / 150** | 91 / 93 / 95 | 40 / 71 / 93 | 47 / 47 / 47 |
| hard | **123 / 132 / 149** | 0 | 0 | 0 |
| rivals only | 1 / 1 / 2 | 56 / 58 / 58 | 86 / 103 / **118** | 19 / 20 / 20 |

unir exceeds the limit by at most 22 ms (at most 8 ms on the images it reads).
Details: [results/speed/speed.md](results/speed/speed.md). Laptop with an
Intel Core i5-1335U, Windows 11; absolute numbers depend on the processor —
compare readers with each other.

### SSCC on a conveyor (synthetic)

There are no public sets of conveyor frames, so this part is synthetic: a
GS1-128 SSCC label (156 modules) next to text and a second GS1-128, nominal
2.2 px per module, one condition changed at a time. Worst value at which a
reader still reads at least 90 % of the frames of a point; symbol almost
horizontal (±5°), 50 frames per point:

| condition | unir | zxing-cpp | ZBar |
|---|---|---|---|
| module size | **from 0.8 px** | from 1.6 px | from 1.4 px |
| blur σ | **up to 2.6 px** | up to 1.2 px | up to 0.6 px |
| noise σ | **up to 70** (end of the range) | up to 18 | up to 3 |
| print contrast | **down to 0.04** | full only (0.3 — 78 %) | down to 0.2 |
| label tilt | **up to 65°** | up to 45° | up to 55° |
| motion blur across the bars | **up to 6 px** | up to 2 px | none |
| JPEG quality | down to 5 for all | | |
| dot gain | ±0.4 module for all | | |

With a random rotation of 0–360° (30 frames per point) unir keeps the same
limits; zxing-cpp reaches 90 % at no point, ZBar only near the nominal.
Wrong SSCC numbers on all 5840 frames: unir 0, zxing-cpp 0, ZBar 4.
OpenCV does not read Code 128 and is not compared.

Truth and every reader's answer per frame:
[synthetic-sscc/frames](synthetic-sscc/frames), per point:
[synthetic-sscc/per_point.csv](synthetic-sscc/per_point.csv). The frames
themselves (PNG and JPEG, 1.3 GB) — in the [v1 release](https://github.com/libscanner/barcode-1d-benchmark/releases/tag/v1).
The generator is not published; the frames are.

## Sets

| set | images with truth | licence | where |
|---|---:|---|---|
| Artelab Medium Barcode 1D, №1 and №2 | 214, 213 | CC BY 3.0 | [artelab.dista.uninsubria.it](http://artelab.dista.uninsubria.it/downloads/datasets/barcode/medium_barcode_1d/medium_barcode_1d.html) (Zamberletti, Gallo, Carullo, Binaghi, 2011) |
| DEAL KAIST: barcode_bb, e8_bb, background | 3200, 89, 788 negative | CC BY 4.0 | [zenodo.org/records/13586402](https://zenodo.org/records/13586402) |
| SmartEngines barcode | 3000 of 3960 | not stated by the authors ** | ftp://smartengines.com/barcode/ (Milovzorov, Bezmaternykh, Arlazarov, doi:10.1117/12.2587628) |
| Open Food Facts | 145 | CC BY-SA (images), ODbL (database) | [lists/off.csv](lists/off.csv) |
| Wikimedia Commons, category Code 128 | 31 images, 38 symbols | per file | [lists/commons.csv](lists/commons.csv) |
| synthetic negatives | 200 negative | MIT-0 (ours) | `harness/negative_synth.py`, seed 7 |

\*\* The authors state no licence for the SmartEngines barcode set (the README on their server has none;
[BenSouchet/barcode-datasets](https://github.com/BenSouchet/barcode-datasets) lists CC BY 4.0 without a source,
the other Smart Engines datasets on the same server are CC BY-SA 2.5). We therefore publish only its
markup-derived truth and the readers' answers — no images.

The images are not copied here: download them from their authors. Expected
layout of `data/`:

```
data/artelab/BarcodeDatasets/Dataset1/*.jpg, Dataset2/*.jpg
data/deal/barcode_bb/..., data/deal/e8_bb/..., data/deal/background/...
data/smartengines/images/..., data/smartengines/markup/...
data/off/*.jpg          python harness/fetch_lists.py --sets off
data/commons/*.jpg      python harness/fetch_lists.py --sets commons
data/negative-synth/    python harness/negative_synth.py data/negative-synth 200 7
```

Ground truth is in [truth/](truth): `file;code;symbology` with the path
relative to the set folder. For Artelab, DEAL and SmartEngines it comes from
the authors' markup (`harness/prepare_truth.py` re-creates the files
byte-for-byte); for Open Food Facts it is the product's code from their
database; for Commons it is the code given by at least two of four sources
(zxing-cpp, ZBar, an early run of our reader, the file name), and codes
given by one source only (column `unsure`) count neither as correct nor as
foreign.

## How to reproduce

```bash
pip install zxing-cpp pyzbar opencv-contrib-python pillow numpy libscanner-unir
python harness/bench.py --data data --color --out results/my-run
```

OpenCV with the super-resolution model needs OpenCV 4.10 in a separate
environment (`--python-cv4 <its python>`) and `sr.prototxt` / `sr.caffemodel`
from [WeChatCV/opencv_3rdparty](https://github.com/WeChatCV/opencv_3rdparty)
(branch `wechat_qrcode`) in `--sr-dir`. The reader calls are in
[harness/bench.py](harness/bench.py) (`_init_reader`) — every rival runs in
the best mode we could find, the same on every image.

Time: `python harness/speed.py prepare --acc results/accuracy-gray --data data --dir speed`,
then `run` and `report`. `speed.py` times unir through its Python package in
process, like the rivals; the published unir times come from an equivalent
in-process C++ probe on the same engine library.

Without a licence key unir runs a 30-day trial ([libscanner.com](https://libscanner.com)).

## Notes

- **Open Food Facts selection.** Many product photos show no barcode at all
  (front side, ingredients), so of the 1258 photos crawled on 2026-10-22 the
  set keeps the 145 where at least one of two readers — an early version of
  our engine or zxing-cpp — read the product code. This favours those two;
  ZBar and OpenCV took no part in the selection.
- **Time and the engine version.** The accuracy numbers are from the unir
  1.2.6 release, the time from unir 1.2.7: with a short limit it first reads a
  large image downscaled; without a limit its answers are byte-for-byte those
  of 1.2.6.
- **We built unir looking at the misses on these same sets**, so this is still
  our home ground, although with someone else's truth. That is why the whole
  bench is published: run it on your own set.
- Muenster BarcodeDB is not reachable at the authors' link any more, BarBeR
  requires registration — neither is included.
- SmartEngines: only images whose symbols are EAN/UPC or Code 128 (its Code
  39, Codabar and Code 93 images are not in the set), a random 3000 of 3960
  (`bench.py --sample 3000 --seed 1`).

## Repository

- `harness/` — `bench.py` (accuracy), `speed.py` (time), `codes.py` (code
  comparison), `prepare_truth.py`, `fetch_lists.py`, `crawl_off.py`,
  `crawl_commons.py`, `negative_synth.py`;
- `truth/`, `lists/` — ground truth and download lists;
- `results/accuracy-color`, `results/accuracy-gray` — per image and reader
  (`<set>-<reader>.tsv`), foreign codes (`aliens.tsv`), summary;
- `results/speed` — sample, raw times of every round, report;
- `synthetic-sscc/` — truth and answers per frame, per-point table.

Code: MIT No Attribution ([LICENSE](LICENSE)). The images belong to their
authors under their licences.
