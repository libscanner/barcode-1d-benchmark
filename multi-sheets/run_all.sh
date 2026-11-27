#!/bin/bash
# All readers one after another on the 377 sheet frames (Linux / WSL). Each process is pinned to one core (CPU 2),
# unir in one thread; the last run is unir in 4 threads on cores 0-3, for reference.
#   bash run_all.sh <frames dir> [python]
set -eu
D=$(cd "$(dirname "$0")" && pwd)
IMG=${1:?frames dir}
PY=${2:-python3}
mkdir -p "$D/results"
run() {   # name reader threads [cores]
    taskset -c "${4:-2}" "$PY" "$D/multi_bench.py" "$2" "$IMG" "$3" "$D/frames.lst" > "$D/results/$1.tsv"
    echo "$1: $(wc -l < "$D/results/$1.tsv") frames"
}
run unir unir 1
run scandit scandit 1
run zxing zxing 1
run opencv opencv 1
run zbar zbar 1
run unir4 unir 4 0-3
"$PY" "$D/multi_sum.py" > "$D/results/summary.md"
