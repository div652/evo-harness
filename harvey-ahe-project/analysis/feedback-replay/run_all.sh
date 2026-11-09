#!/usr/bin/env bash
# Run the [VERIFIER FEEDBACK] wrapper experiment end to end (replays, blind judging, summaries).
# Usage, from anywhere: bash harvey-ahe-project/analysis/feedback-replay/run_all.sh   (in tmux)
set -u
cd /home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
D=analysis/feedback-replay; L=$D/logs; mkdir -p $L
log() { echo "[$(TZ=Asia/Kolkata date +%F' '%T) IST] $*" | tee -a $L/run_all.log; }
for target in first_error first_strict; do
  for variant in control wrapped; do
    log "replay $target $variant"
    python3 $D/replay.py --target $target --variant $variant --samples 2 --workers 8 >> $L/replay_${target}_${variant}.log 2>&1
  done
  for arm in original control wrapped; do
    log "judge $target $arm"
    python3 $D/judge.py --target $target --arm $arm --workers 8 >> $L/judge_${target}_${arm}.log 2>&1
  done
  python3 $D/summarize.py --target $target --arms original control wrapped >> $L/summarize.log 2>&1
  log "done $target"
done
log "all done"
