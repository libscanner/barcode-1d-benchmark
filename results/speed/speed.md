# 1D speed by image groups (3 rounds, one thread, one core)

Time is the read call only, the image is already in memory (PGM, greyscale); minimum over rounds. unir looks for one code (early exit); "within B" for unir is a run with budget_ms = B, counted only if it kept the limit; for rivals — read within <= B ms.

## clear (all read) — 150 images, median 1.9 MP

Sets: deal 101, artelab-1 18, smartengines 16, off 9, deal-e8 6

| Reader | median, ms | p90, ms | read without limit | within 60 ms | within 100 ms | within 500 ms |
|---|---|---|---|---|---|---|
| **unir**, one code | 14 | 145 | 150 | 139 | 148 (148–149) | 150 |
| zxing | 20 | 91 | 150 | 131 | 141 | 150 |
| zbar | 171 | 965 | 150 | 23 | 59 | 112 |
| opencv | 13 | 28 | 148 | 148 | 148 | 148 |
| opencv-sr | 20 | 45 | 150 | 149 | 150 | 150 |

unir limit: largest overrun 8 ms.

## medium (unir and some rivals) — 150 images, median 0.6 MP

Sets: deal 69, smartengines 60, artelab-2 10, deal-e8 4, off 4, commons-c128 2, artelab-1 1

| Reader | median, ms | p90, ms | read without limit | within 60 ms | within 100 ms | within 500 ms |
|---|---|---|---|---|---|---|
| **unir**, one code | 10 | 132 | 150 | 134 (134–135) | 141 (140–142) | 150 |
| zxing | 9 | 27 | 95 | 91 | 93 | 95 |
| zbar | 71 | 263 | 102 | 40 | 71 | 93 |
| opencv | 12 | 22 | 43 | 43 | 43 | 43 |
| opencv-sr | 16 | 44 | 47 | 47 | 47 | 47 |

unir limit: largest overrun 5 ms.

## hard (unir only) — 150 images, median 0.6 MP

Sets: smartengines 89, deal 44, artelab-2 14, commons-c128 1, deal-e8 1, off 1

| Reader | median, ms | p90, ms | read without limit | within 60 ms | within 100 ms | within 500 ms |
|---|---|---|---|---|---|---|
| **unir**, one code | 11 | 194 | 150 | 123 (122–123) | 132 | 149 (149–150) |
| zxing | 7 | 19 | 0 | 0 | 0 | 0 |
| zbar | 67 | 182 | 0 | 0 | 0 | 0 |
| opencv | 11 | 17 | 0 | 0 | 0 | 0 |
| opencv-sr | 15 | 45 | 0 | 0 | 0 | 0 |

unir limit: largest overrun 5 ms.

## rivals only — 150 images, median 0.4 MP

Sets: smartengines 110, deal 31, off 5, artelab-2 2, deal-e8 2

| Reader | median, ms | p90, ms | read without limit | within 60 ms | within 100 ms | within 500 ms |
|---|---|---|---|---|---|---|
| **unir**, one code | 152 | 642 | 2 | 1 | 1 | 2 |
| zxing | 5 | 16 | 58 | 56 | 58 | 58 |
| zbar | 43 | 152 | 120 | 86 | 103 | 118 |
| opencv | 10 | 18 | 16 | 16 | 16 | 16 |
| opencv-sr | 14 | 34 | 20 | 19 | 20 | 20 |

unir limit: largest overrun 22 ms.

## nobody — 150 images, median 0.4 MP

Sets: smartengines 131, deal 12, artelab-2 7

| Reader | median, ms | p90, ms | read without limit | within 60 ms | within 100 ms | within 500 ms |
|---|---|---|---|---|---|---|
| **unir**, one code | 43 | 275 | 0 | 0 | 0 | 0 |
| zxing | 4 | 8 | 0 | 0 | 0 | 0 |
| zbar | 38 | 89 | 0 | 0 | 0 | 0 |
| opencv | 8 | 13 | 0 | 0 | 0 | 0 |
| opencv-sr | 12 | 28 | 0 | 0 | 0 | 0 |

unir limit: largest overrun 7 ms.

## no code — 150 images, median 0.3 MP

Sets: negative-lines 118, negative-deal 25, negative-synth 7

| Reader | median, ms | p90, ms | codes returned (false) |
|---|---|---|---|
| **unir**, one code | 39 | 201 | 0 |
| zxing | 4 | 8 | 0 |
| zbar | 40 | 61 | 0 |
| opencv | 7 | 9 | 0 |
| opencv-sr | 8 | 10 | 0 |

unir limit: largest overrun 6 ms.

