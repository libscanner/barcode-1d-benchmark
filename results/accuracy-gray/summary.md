# 1D accuracy bench

Share = correct / symbols with truth; precision = correct / (correct + single foreign); foreign = returned code not in the truth, «single+confirmed» (confirmed — another engine returned it too: most likely a real second code in the image). On negative sets everything returned is foreign.

| Set | images | symbols | unir | zxing | zbar | opencv | opencv-sr | union | unir only | rivals only |
|---|---|---|---|---|---|---|---|---|---|---|
| artelab-1 | 215 | 214 | 211 (98.6 %), p. 100.0 %, foreign 0+1 | 193 (90.2 %), p. 99.5 %, foreign 1+0 | 200 (93.5 %), p. 97.1 %, foreign 6+0 | 206 (96.3 %), p. 99.5 %, foreign 1+1 | 206 (96.3 %), p. 99.5 %, foreign 1+1 | 214 | 1 | 3 |
| artelab-2 | 215 | 213 | 152 (71.4 %), p. 98.7 %, foreign 2+0 | 32 (15.0 %), p. 86.5 %, foreign 5+0 | 34 (16.0 %), p. 77.3 %, foreign 10+0 | 88 (41.3 %), p. 91.7 %, foreign 8+0 | 89 (41.8 %), p. 90.8 %, foreign 9+0 | 158 | 63 | 6 |
| deal | 3200 | 3200 | 2873 (89.8 %), p. 100.0 %, foreign 0+6 | 2369 (74.0 %), p. 98.3 %, foreign 42+5 | 2385 (74.5 %), p. 97.7 %, foreign 57+5 | 2153 (67.3 %), p. 98.3 %, foreign 38+3 | 2244 (70.1 %), p. 97.4 %, foreign 60+3 | 2949 | 182 | 76 |
| deal-e8 | 90 | 89 | 84 (94.4 %), p. 100.0 %, foreign 0+1 | 79 (88.8 %), p. 100.0 %, foreign 0+1 | 80 (89.9 %), p. 97.6 %, foreign 2+1 | 62 (69.7 %), p. 100.0 %, foreign 0+0 | 62 (69.7 %), p. 100.0 %, foreign 0+0 | 88 | 1 | 4 |
| smartengines | 3000 | 3000 | 1387 (46.2 %), p. 100.0 %, foreign 0+0 | 892 (29.7 %), p. 99.6 %, foreign 4+0 | 1030 (34.3 %), p. 99.6 %, foreign 4+0 | 224 (7.5 %), p. 90.3 %, foreign 24+0 | 222 (7.4 %), p. 88.4 %, foreign 29+0 | 1625 | 357 | 238 |
| off | 145 | 145 | 137 (94.5 %), p. 99.3 %, foreign 1+2 | 125 (86.2 %), p. 96.9 %, foreign 4+2 | 120 (82.8 %), p. 99.2 %, foreign 1+2 | 94 (64.8 %), p. 100.0 %, foreign 0+0 | 96 (66.2 %), p. 100.0 %, foreign 0+0 | 145 | 6 | 8 |
| commons-c128 | 55 | 38 | 37 (97.4 %), p. 92.5 %, foreign 3+0 | 34 (89.5 %), p. 100.0 %, foreign 0+0 | 33 (86.8 %), p. 100.0 %, foreign 0+0 | 0 (0.0 %), p. 0.0 %, foreign 3+0 | 0 (0.0 %), p. 0.0 %, foreign 3+0 | 38 | 1 | 1 |
| negative-deal | 788 | 0 | false 0+0 | false 0+0 | false 0+0 | false 1+0 | false 1+0 | 0 | 0 | 0 |
| negative-synth | 200 | 0 | false 0+0 | false 0+0 | false 0+0 | false 6+0 | false 6+0 | 0 | 0 | 0 |
| **total** | | 6899 | **4881 (70.7 %)** | **3724 (54.0 %)** | **3882 (56.3 %)** | **2827 (41.0 %)** | **2919 (42.3 %)** | | | |

## By symbology

| Set | symbology | symbols | unir | zxing | zbar | opencv | opencv-sr |
|---|---|---|---|---|---|---|---|
| artelab-1 | ean | 214 | 211 (98.6 %) | 193 (90.2 %) | 200 (93.5 %) | 206 (96.3 %) | 206 (96.3 %) |
| artelab-2 | ean | 213 | 152 (71.4 %) | 32 (15.0 %) | 34 (16.0 %) | 88 (41.3 %) | 89 (41.8 %) |
| deal | ean | 3200 | 2873 (89.8 %) | 2369 (74.0 %) | 2385 (74.5 %) | 2153 (67.3 %) | 2244 (70.1 %) |
| deal-e8 | ean | 89 | 84 (94.4 %) | 79 (88.8 %) | 80 (89.9 %) | 62 (69.7 %) | 62 (69.7 %) |
| smartengines | ean | 1790 | 1014 (56.6 %) | 755 (42.2 %) | 890 (49.7 %) | 224 (12.5 %) | 222 (12.4 %) |
| smartengines | c128 | 1210 | 373 (30.8 %) | 137 (11.3 %) | 140 (11.6 %) | 0 (0.0 %) | 0 (0.0 %) |
| off | ean | 145 | 137 (94.5 %) | 125 (86.2 %) | 120 (82.8 %) | 94 (64.8 %) | 96 (66.2 %) |
| commons-c128 | ean | 3 | 3 (100.0 %) | 2 (66.7 %) | 3 (100.0 %) | 0 (0.0 %) | 0 (0.0 %) |
| commons-c128 | c128 | 35 | 34 (97.1 %) | 32 (91.4 %) | 30 (85.7 %) | 0 (0.0 %) | 0 (0.0 %) |

## Read by a rival only (symbols unir did not read)

- artelab-1: 3 — opencv 2, opencv-sr 2, zbar 3
- artelab-2: 6 — opencv 5, opencv-sr 4, zxing 1
- deal: 76 — opencv 23, opencv-sr 33, zbar 44, zxing 47
- deal-e8: 4 — opencv 1, opencv-sr 1, zbar 3, zxing 2
- smartengines: 238 — opencv 3, opencv-sr 3, zbar 214, zxing 66
- off: 8 — opencv 2, opencv-sr 2, zbar 6, zxing 8
- commons-c128: 1 — zbar 1, zxing 1

## Readers

- unir: unir 1.2.7, `unir --batch <list> --sym ean,128,gs1 --codes 0 --timeout-ms 0 --single --corners`
- zxing: zxing-cpp 3.1.1 rotate+downscale+invert LocalAverage|GlobalHistogram Plain
- zbar: pyzbar 0.1.9 image + inverted + rotated 45°
- opencv: OpenCV 5.0.0 BarcodeDetector without a model
- opencv-sr: OpenCV 4.10.0 BarcodeDetector with the WeChat super-resolution model
