#!/usr/bin/env bash
# Campaign 28: the stage-protocol harness on training tasks
# (see the config) through the CAO gateway. Runs
# scripts/run_c0_train_only.py; after a non-zero exit (e.g. a `podman info`
# timeout) it is rerun, which resumes the evaluation, up to MAX_INVOCATIONS
# launches, 120 s apart. Completed units are kept.
#
# Usage, inside tmux, from anywhere:  bash harvey-ahe-project/scripts/run_c28.sh
set -u
cd /home/agarwaldi/AHE_Harvey_cao
P=harvey-ahe-project
A=$P/campaign-artifacts
PY=/home/agarwaldi/AHE_Harvey/.venv/bin/python
CFG=${CFG:-$P/ahe-cao-c28-stage-smoke3.yaml}
TAG=${TAG:-c28}
MAX_INVOCATIONS=${MAX_INVOCATIONS:-12}
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
export PYTHONPATH=$PWD/src:$PWD/$P
log() { echo "[$TAG $(date -u +%FT%TZ)] $*" | tee -a $A/$TAG-run.log; }
/home/agarwaldi/cao/cao.sh status | grep -q running || { log "CAO gateway not running"; exit 1; }
$PY -c "from pathlib import Path; from ahe_runner.config import load_config; load_config(Path('$CFG'))" \
  || { log "config does not load"; exit 1; }
for i in $(seq 1 "$MAX_INVOCATIONS"); do
  log "invocation $i"
  $PY $P/scripts/run_c0_train_only.py --config $CFG >> $A/$TAG-run-detail.log 2>&1
  rc=$?; echo "EXIT=$rc" >> $A/$TAG-run-detail.log; log "invocation $i exit $rc"
  [ "$rc" -eq 0 ] && { log "all done"; exit 0; }
  sleep 120
done
log "gave up after $MAX_INVOCATIONS invocations"; exit 1
