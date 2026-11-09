#!/usr/bin/env bash
# Campaign 34: campaign 23 rerun with reasoning summaries (gpt-5.6-luna agent,
# gpt-5.6-sol judge and meta agents, all-pass objective) through the CAO gateway. `ahe run` starts
# it; after a non-zero exit (e.g. a `podman info` timeout) `ahe resume`
# continues it, up to MAX_INVOCATIONS launches in total, 120 s apart. Completed
# units and stages are kept.
#
# Usage, inside tmux, from anywhere:  bash harvey-ahe-project/scripts/run_c34.sh
set -u
cd /home/agarwaldi/AHE_Harvey_cao
P=harvey-ahe-project
A=$P/campaign-artifacts
CFG=$P/ahe-cao-c34-c23-rerun-summaries.yaml
MAX_INVOCATIONS=${MAX_INVOCATIONS:-12}
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
export PYTHONPATH=$PWD/src:$PWD/$P
AHE="/home/agarwaldi/AHE_Harvey/.venv/bin/python -m ahe_runner.cli"
log() { echo "[c34 $(date -u +%FT%TZ)] $*" | tee -a $A/c34-run.log; }
/home/agarwaldi/cao/cao.sh status | grep -q running || { log "CAO gateway not running"; exit 1; }
cmd=run
[ -f "$A/harvey-lab-campaign-34-c23-rerun-summaries-80-20-70/campaign_state.json" ] && cmd=resume
for i in $(seq 1 "$MAX_INVOCATIONS"); do
  log "invocation $i: ahe $cmd"
  $AHE $cmd --config $CFG >> $A/c34-ahe.log 2>&1
  rc=$?; echo "EXIT=$rc" >> $A/c34-ahe.log; log "invocation $i exit $rc"
  [ "$rc" -eq 0 ] && exit 0
  cmd=resume
  sleep 120
done
exit 1
