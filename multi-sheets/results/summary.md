# 377 frames: EAN-13 sheet 228, SSCC (GS1-128) sheet 149; frames nobody read anything on: 0

One core, unir in one thread (except the "4 threads" row); barcodes only; time = the read call only.

| reader | correct | of 20 × frames | whole sheets | foreign | EAN-13 | SSCC (GS1-128) | median, ms | p90, ms | CPU / wall |
|---|---|---|---|---|---|---|---|---|---|
| unir 1.2.18 | 7305 | 96.9 % | 342 | 0 | 4396 (96.4 %) | 2909 (97.6 %) | 267 | 529 | 1.00 |
| Scandit 8.7.1 | 7277 | 96.5 % | 327 | 0 | 4379 (96.0 %) | 2898 (97.2 %) | 285 | 744 | 1.00 |
| zxing-cpp 3.1.1 | 5738 | 76.1 % | 180 | 2 | 4032 (88.4 %) | 1706 (57.2 %) | 33 | 44 | 1.00 |
| ZBar 0.23.93 | 3790 | 50.3 % | 3 | 972 | 3537 (77.6 %) | 253 (8.5 %) | 658 | 1017 | 1.00 |
| OpenCV 5.1 | 3936 | 52.2 % | 123 | 490 | 3936 (86.3 %) | 0 (0.0 %) | 17 | 27 | 1.00 |
| unir 1.2.18, 4 threads | 7305 | 96.9 % | 342 | 0 | 4396 (96.4 %) | 2909 (97.6 %) | 172 | 304 | 2.72 |

## Time by sheet, median / p90, ms

| reader | EAN-13 | SSCC (GS1-128) |
|---|---|---|
| unir 1.2.18 | 282 / 567 | 198 / 516 |
| Scandit 8.7.1 | 222 / 369 | 517 / 867 |
| zxing-cpp 3.1.1 | 31 / 42 | 39 / 44 |
| ZBar 0.23.93 | 604 / 848 | 913 / 1369 |
| OpenCV 5.1 | 16 / 19 | 25 / 27 |
| unir 1.2.18, 4 threads | 181 / 332 | 140 / 271 |

## Only unir / only the other reader (codes)

- Scandit 8.7.1: only unir 74, only Scandit 46
- zxing-cpp 3.1.1: only unir 1571, only zxing-cpp 4
- ZBar 0.23.93: only unir 3515, only ZBar 0
- OpenCV 5.1: only unir 3371, only OpenCV 2
- read by any reader: 7355; by none: 185

## Frames by codes of the sheet read (0–5 / 6–10 / 11–15 / 16–19 / 20)

- unir 1.2.18: 2 / 5 / 15 / 13 / 342
- Scandit 8.7.1: 3 / 6 / 11 / 30 / 327
- zxing-cpp 3.1.1: 47 / 38 / 41 / 71 / 180
- ZBar 0.23.93: 156 / 12 / 34 / 172 / 3
- OpenCV 5.1: 155 / 18 / 34 / 47 / 123
- unir 1.2.18, 4 threads: 2 / 5 / 15 / 13 / 342
