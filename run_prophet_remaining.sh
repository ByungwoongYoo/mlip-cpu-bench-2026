#!/usr/bin/env bash
# One-solid-per-process driver for Prophet, used after the sequential Prophet job was killed by the
# 3000 MB RSS watchdog on B. Same job.sh pipeline (2 cores, nice 10, 2 threads, RSS watchdog).
# Skips any solid that already has a result JSON. B gets one retry at a 3500 MB limit.
set -uo pipefail
cd "$(dirname "$0")"
PY=${PROPHET_PY:-${MLIP_VENVS:-$PWD/venvs}/prophet/bin/python}
CORES=${CORES:-6,7}
for s in Pb Ga As Sb Bi Mg Sc Ti Cr Fe Co Zn Y Zr Tc Ru Cd In Lu Hf Re Os Tl Po; do
  if [ -f results/prophet/$s.json ]; then echo "skip $s (JSON exists)"; continue; fi
  MAXMB=${MAXMB:-3000} ./job.sh prophet__$s $CORES $PY -W ignore $PWD/bench_mlip.py --model prophet --threads 2 --solids $s
  [ -f results/prophet/$s.json ] && cp results/prophet/_run.json logs/prophet__$s.run.json
done
if [ ! -f results/prophet/B.json ]; then
  MAXMB=3500 ./job.sh prophet__B $CORES $PY -W ignore $PWD/bench_mlip.py --model prophet --threads 2 --solids B
  [ -f results/prophet/B.json ] && cp results/prophet/_run.json logs/prophet__B.run.json
fi
echo ALL_DONE
