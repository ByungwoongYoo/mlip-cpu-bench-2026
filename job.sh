#!/bin/bash
# usage: job.sh NAME CORES CMD...   -> runs under taskset+nice, RSS watchdog (MAXMB env, default 3800), logs/NAME.log, logs/NAME.res
NAME=$1; CORES=$2; shift 2
MAXMB=${MAXMB:-3800}
LOG=logs/$NAME.log; RES=logs/$NAME.res
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 TORCH_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
start=$(date +%s)
( exec taskset -c $CORES nice -n 10 "$@" ) > $LOG 2>&1 &
PID=$!
peak=0
while kill -0 $PID 2>/dev/null; do
  pids=$(pstree -pT $PID | grep -o '([0-9]*)' | tr -d '()')
  rss=0; for p in $pids; do r=$(awk '/VmRSS/{print $2}' /proc/$p/status 2>/dev/null); rss=$((rss+${r:-0})); done
  mb=$((rss/1024)); [ $mb -gt $peak ] && peak=$mb
  if [ $mb -gt $MAXMB ]; then echo "WATCHDOG KILL rss=${mb}MB > $MAXMB" >> $LOG; pkill -9 -P $PID; kill -9 $PID; fi
  sleep 1
done
wait $PID; rc=$?
end=$(date +%s)
echo "name=$NAME rc=$rc wall_s=$((end-start)) peak_rss_mb=$peak cores=$CORES finished=$(date '+%F %T %Z')" | tee $RES
