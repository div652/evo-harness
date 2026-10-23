#!/usr/bin/env bash
# Campaigns 20/20b on CAO: after 20b's first invocation ends, resume any
# campaign whose last invocation did not exit 0 (e.g. units that hit a
# `podman info` timeout), one campaign at a time, at most MAX_INVOCATIONS
# extra invocations each. Completed units are kept; a resume reruns the rest.
set -u
cd /home/agarwaldi/AHE_Harvey_cao
A=harvey-ahe-project/campaign-artifacts
MAX_INVOCATIONS=${MAX_INVOCATIONS:-5}
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
export PYTHONPATH=$PWD/src:$PWD/harvey-ahe-project
log() { echo "[c20-resume $(date -u +%FT%TZ)] $*" >> $A/c20-resume.log; }
log "waiting for campaign 20b's first invocation to end"
until grep -q '^EXIT=' $A/c20b-cao-run.log; do sleep 60; done
for c in "c20:ahe-cao-c20-c0-ravi100.yaml" "c20b:ahe-cao-c20b-c0-rest150.yaml"; do
  name=${c%%:*}; cfg=${c#*:}; runlog=$A/$name-cao-run.log
  for i in $(seq 1 "$MAX_INVOCATIONS"); do
    last=$(grep '^EXIT=' "$runlog" | tail -1)
    [ "$last" = "EXIT=0" ] && { log "$name complete"; break; }
    log "$name last $last; resume $i/$MAX_INVOCATIONS"
    sleep 60
    /home/agarwaldi/AHE_Harvey/.venv/bin/python harvey-ahe-project/scripts/run_c0_train_only.py \
      --config harvey-ahe-project/$cfg >> "$runlog" 2>&1
    echo "EXIT=$?" >> "$runlog"
  done
done
log "done: c20 $(grep '^EXIT=' $A/c20-cao-run.log | tail -1), c20b $(grep '^EXIT=' $A/c20b-cao-run.log | tail -1)"
