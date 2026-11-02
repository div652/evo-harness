#!/usr/bin/env bash
# Campaign 21: campaign 12's checkpoints C0, C5-C10 on its 20 validation
# tasks (2 trials each) through the CAO gateway, all 7 side by side so that
# backend drift over time affects every checkpoint equally. Each campaign is
# resumed after an infrastructure failure (e.g. a `podman info` timeout) up
# to MAX_INVOCATIONS times; completed units are kept.
#
# Usage, inside tmux, from anywhere:  bash harvey-ahe-project/scripts/run_c21.sh
set -u
cd /home/agarwaldi/AHE_Harvey_cao
A=harvey-ahe-project/campaign-artifacts
MAX_INVOCATIONS=${MAX_INVOCATIONS:-6}
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
export PYTHONPATH=$PWD/src:$PWD/harvey-ahe-project
log() { echo "[c21 $(date -u +%FT%TZ)] $*" | tee -a $A/c21-run.log; }
run_one() {
  local c=$1 runlog=$A/c21-$1-run.log
  for i in $(seq 1 "$MAX_INVOCATIONS"); do
    log "$c invocation $i"
    /home/agarwaldi/AHE_Harvey/.venv/bin/python harvey-ahe-project/scripts/run_c0_train_only.py \
      --config harvey-ahe-project/ahe-cao-c21-c12val-$c.yaml >> "$runlog" 2>&1
    rc=$?; echo "EXIT=$rc" >> "$runlog"; log "$c invocation $i exit $rc"
    [ "$rc" -eq 0 ] && return 0
    sleep 120
  done
  return 1
}
/home/agarwaldi/cao/cao.sh status | grep -q running || { log "CAO gateway not running"; exit 1; }
pids=()
for c in C0 C5 C6 C7 C8 C9 C10; do run_one "$c" & pids+=($!); sleep 20; done
for p in "${pids[@]}"; do wait "$p"; done
log "all done: $(for c in C0 C5 C6 C7 C8 C9 C10; do echo -n "$c $(grep '^EXIT=' $A/c21-$c-run.log | tail -1)  "; done)"
