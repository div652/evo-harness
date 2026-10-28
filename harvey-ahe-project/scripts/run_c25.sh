#!/usr/bin/env bash
# Campaign 25: every campaign 23 checkpoint (C0-C10, copied to harness_c25/)
# rerun on campaign 23's 20 validation tasks (splits-firm-knowledge-c25-c23val20.json),
# 1 trial each, through the CAO gateway. Two lanes run side by side, each
# working through its checkpoints in turn with scripts/run_c0_train_only.py.
# After a non-zero exit (e.g. a `podman info` timeout) a checkpoint is rerun,
# which resumes its evaluation, up to MAX_INVOCATIONS launches, 120 s apart.
#
# Usage, inside tmux, from anywhere:  bash harvey-ahe-project/scripts/run_c25.sh
set -u
cd /home/agarwaldi/AHE_Harvey_cao
P=harvey-ahe-project
A=$P/campaign-artifacts
PY=/home/agarwaldi/AHE_Harvey/.venv/bin/python
MAX_INVOCATIONS=${MAX_INVOCATIONS:-12}
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
export PYTHONPATH=$PWD/src:$PWD/$P
log() { echo "[c25 $(date -u +%FT%TZ)] $*" | tee -a $A/c25-run.log; }
/home/agarwaldi/cao/cao.sh status | grep -q running || { log "CAO gateway not running"; exit 1; }
run_one() {
  local C=$1 CFG=$P/ahe-cao-c25-val20-c23$1.yaml i rc
  for i in $(seq 1 "$MAX_INVOCATIONS"); do
    log "$C invocation $i"
    $PY $P/scripts/run_c0_train_only.py --config $CFG >> $A/c25-$C-run.log 2>&1
    rc=$?; echo "EXIT=$rc" >> $A/c25-$C-run.log; log "$C invocation $i exit $rc"
    [ "$rc" -eq 0 ] && return 0
    sleep 120
  done
  return 1
}
lane() { local C r=0; for C in "$@"; do run_one $C || r=1; done; return $r; }
for i in $(seq 0 10); do
  $PY -c "from pathlib import Path; from ahe_runner.config import load_config; load_config(Path('$P/ahe-cao-c25-val20-c23C$i.yaml'))" \
    || { log "config for C$i does not load"; exit 1; }
done
lane C0 C2 C4 C6 C8 C10 & pa=$!
sleep 60
lane C1 C3 C5 C7 C9 & pb=$!
wait $pa; ra=$?; wait $pb; rb=$?
log "all done: lane A $ra, lane B $rb"
