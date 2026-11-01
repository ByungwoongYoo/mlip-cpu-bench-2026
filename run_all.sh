#!/usr/bin/env bash
# Runs every model sequentially on the same 2 cores (fair wall-time comparison), nice 10, RSS watchdog 3000 MB.
# One virtualenv per model under $MLIP_VENVS (default ./venvs): matgl, mace, upet, prophet, flashcart.
# Prophet and FlashCart also need MLIP_MODEL_DIR (see README). Run ./fetch_refs.sh first.
set -uo pipefail
cd "$(dirname "$0")"
V=${MLIP_VENVS:-$PWD/venvs}
CORES=${CORES:-6,7}
mkdir -p logs
declare -A VENV=( [flashcart_mad]=flashcart [chgnet_r2scan]=matgl [mace_mp]=mace [pet_mad_s]=upet [prophet]=prophet )
for m in ${MODELS:-chgnet_r2scan mace_mp pet_mad_s prophet flashcart_mad}; do
  MAXMB=3000 ./job.sh $m $CORES $V/${VENV[$m]}/bin/python -W ignore $PWD/bench_mlip.py --model $m --threads 2
done
