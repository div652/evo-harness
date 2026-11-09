#!/usr/bin/env bash
# Run the [VERIFIER FEEDBACK] wrapper experiment end to end (replays, blind judging, summaries), 24 calls at a time.
# first_error: original vs control vs wrapped (control checks that replays reproduce the recorded behaviour).
# first_strict: original vs wrapped (the recorded step is the baseline).
# Usage, from anywhere: bash harvey-ahe-project/analysis/feedback-replay/run_all.sh   (in tmux)
set -u
cd /home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
D=analysis/feedback-replay; L=$D/logs; W=24; mkdir -p $L
log() { echo "[$(TZ=Asia/Kolkata date +%F' '%T) IST] $*" | tee -a $L/run_all.log; }
run_target() {  # target, then the replay variants; the judged arms are original + those variants
  local target=$1; shift
  for variant in "$@"; do
    log "replay $target $variant"
    python3 $D/replay.py --target $target --variant $variant --samples 2 --workers $W >> $L/replay_${target}_${variant}.log 2>&1
  done
  for arm in original "$@"; do
    log "judge $target $arm"
    python3 $D/judge.py --target $target --arm $arm --workers $W >> $L/judge_${target}_${arm}.log 2>&1
  done
  python3 $D/summarize.py --target $target --arms original "$@" >> $L/summarize.log 2>&1
  log "done $target"
}
run_target first_error control wrapped
run_target first_strict wrapped
log "all done"
