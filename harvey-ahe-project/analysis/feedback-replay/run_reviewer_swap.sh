#!/usr/bin/env bash
# Reviewer swap on the 237 first-error items: fresh gpt-5.6-luna (medium) and fresh claude-sonnet-5-5 reviews,
# each followed by one replayed agent step. 4 jobs x 6 workers = 24 concurrent calls.
set -u
cd /home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
D=analysis/feedback-replay; L=$D/logs; mkdir -p $L
log() { echo "[$(TZ=Asia/Kolkata date +%F' '%T) IST] $*" | tee -a $L/run_reviewer_swap.log; }
log "start"
for r in r2 r3; do for v in luna sonnet; do
  python3 $D/reviewer_swap.py --round $r --reviewer $v --samples 2 --workers 6 >> $L/reviewer_swap_${r}_${v}.log 2>&1 &
done; done
wait
log "replays done"
