#!/usr/bin/env bash
# Watches campaign 23: when run_c23.sh is no longer running and its last
# invocation did not exit 0, relaunches it (which resumes the campaign; done
# work is kept). Gives up after MAX_RELAUNCHES relaunches.
#
# Usage, inside tmux:  bash harvey-ahe-project/scripts/watch_c23.sh
set -u
cd /home/agarwaldi/AHE_Harvey_cao
A=harvey-ahe-project/campaign-artifacts
MAX_RELAUNCHES=${MAX_RELAUNCHES:-5}
CHECK_SECONDS=${CHECK_SECONDS:-300}
log() { echo "[c23-watch $(date -u +%FT%TZ)] $*" | tee -a $A/c23-run.log; }
running() {
  pgrep -f "scripts/run_c23.sh" >/dev/null || pgrep -f "ahe-cao-c23-luna-allpass.yaml" >/dev/null
}
relaunches=0
log "watcher started (max $MAX_RELAUNCHES relaunches, check every ${CHECK_SECONDS}s)"
while true; do
  sleep "$CHECK_SECONDS"
  running && continue
  if grep -v "c23-watch" $A/c23-run.log | tail -1 | grep -q "exit 0$"; then
    log "campaign finished (exit 0); watcher done"
    exit 0
  fi
  if [ "$relaunches" -ge "$MAX_RELAUNCHES" ]; then
    log "run_c23.sh stopped and $MAX_RELAUNCHES relaunches used; giving up"
    exit 1
  fi
  relaunches=$((relaunches + 1))
  log "run_c23.sh not running and campaign unfinished; relaunch $relaunches"
  bash harvey-ahe-project/scripts/run_c23.sh
done
