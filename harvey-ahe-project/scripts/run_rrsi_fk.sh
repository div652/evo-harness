#!/usr/bin/env bash
# RRSI firm-knowledge campaign (80 train / 40 test, 20 rounds):
# non-zero exit, `ahe resume`, up to MAX_INVOCATIONS launches, 120 s apart.
# Usage, inside tmux:  bash ~/rrsi-pilot/run_pilot.sh
set -u
cd /home/agarwaldi/rrsi-pilot/harvey-ahe-project
A=campaign-artifacts
mkdir -p $A
CFG=ahe-rrsi-fk-80-40.yaml
MAX_INVOCATIONS=${MAX_INVOCATIONS:-40}
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
export PYTHONPATH=$PWD
AHE="/home/agarwaldi/rrsi-pilot/.venv/bin/python -m ahe_runner"
log() { echo "[rrsi-fk $(date -u +%FT%TZ)] $*" | tee -a $A/rrsi-fk-run.log; }
/home/agarwaldi/cao/cao.sh status | grep -q running || { log "CAO gateway not running"; exit 1; }
cmd=run
[ -f "$A/rrsi-fk-cao-luna-80-40/campaign_state.json" ] && cmd=resume
for i in $(seq 1 "$MAX_INVOCATIONS"); do
  log "invocation $i: ahe $cmd"
  $AHE $cmd --config $CFG >> $A/rrsi-fk-ahe.log 2>&1
  rc=$?; echo "EXIT=$rc" >> $A/rrsi-fk-ahe.log; log "invocation $i exit $rc"
  [ "$rc" -eq 0 ] && exit 0
  cmd=resume
  sleep 120
done
exit 1
