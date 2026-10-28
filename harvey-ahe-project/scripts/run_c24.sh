#!/usr/bin/env bash
# Campaign 24: campaign 23's C0 and C3, 3 trials each on the 50 held-out tasks
# (splits-firm-knowledge-c24-heldout50.json), side by side through the CAO
# gateway. Each runs scripts/run_c0_train_only.py; after a non-zero exit (e.g.
# a `podman info` timeout) it is rerun, which resumes the evaluation, up to
# MAX_INVOCATIONS launches, 120 s apart. Completed units are kept.
#
# Usage, inside tmux, from anywhere:  bash harvey-ahe-project/scripts/run_c24.sh
set -u
cd /home/agarwaldi/AHE_Harvey_cao
P=harvey-ahe-project
A=$P/campaign-artifacts
PY=/home/agarwaldi/AHE_Harvey/.venv/bin/python
MAX_INVOCATIONS=${MAX_INVOCATIONS:-12}
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
export PYTHONPATH=$PWD/src:$PWD/$P
log() { echo "[c24 $(date -u +%FT%TZ)] $*" | tee -a $A/c24-run.log; }
/home/agarwaldi/cao/cao.sh status | grep -q running || { log "CAO gateway not running"; exit 1; }
run_one() {
  local C=$1 CFG=$P/ahe-cao-c24-heldout50-c23$1.yaml i rc
  for i in $(seq 1 "$MAX_INVOCATIONS"); do
    log "$C invocation $i"
    $PY $P/scripts/run_c0_train_only.py --config $CFG >> $A/c24-$C-run.log 2>&1
    rc=$?; echo "EXIT=$rc" >> $A/c24-$C-run.log; log "$C invocation $i exit $rc"
    [ "$rc" -eq 0 ] && return 0
    sleep 120
  done
  return 1
}
for C in C0 C3; do
  $PY -c "from pathlib import Path; from ahe_runner.config import load_config; load_config(Path('$P/ahe-cao-c24-heldout50-c23$C.yaml'))" \
    || { log "config for $C does not load"; exit 1; }
done
run_one C0 & p0=$!
sleep 60
run_one C3 & p3=$!
wait $p0; r0=$?; wait $p3; r3=$?
log "all done: C0 $r0, C3 $r3"
