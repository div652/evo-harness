#!/usr/bin/env bash
# Reviewer swap with gpt-5.6-luna at HIGH reasoning effort on the 237 first-error items, then judging and summary. 24 concurrent calls.
set -u
cd /home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
D=analysis/feedback-replay; L=$D/logs
log() { echo "[$(TZ=Asia/Kolkata date +%F' '%T) IST] $*" | tee -a $L/run_reviewer_luna_high.log; }
log "replays start"
python3 $D/reviewer_swap.py --round r2 --reviewer luna_high --samples 2 --workers 12 >> $L/reviewer_swap_r2_luna_high.log 2>&1 &
python3 $D/reviewer_swap.py --round r3 --reviewer luna_high --samples 2 --workers 12 >> $L/reviewer_swap_r3_luna_high.log 2>&1 &
wait
for r in r2 r3; do python3 $D/reviewer_swap.py --round $r --reviewer luna_high --samples 2 --workers 4 >> $L/reviewer_swap_${r}_luna_high.log 2>&1; done  # retry any failures
log "judging"
python3 $D/judge_problem.py --arm reviewer_luna_high --workers 24 >> $L/judge_problem_reviewer_luna_high.log 2>&1
python3 $D/judge_problem.py --arm reviewer_luna_high --workers 4 >> $L/judge_problem_reviewer_luna_high.log 2>&1
python3 $D/judge_problem.py --summarize original control_nosum reviewer_sonnet reviewer_luna reviewer_luna_high >> $L/judge_problem_summary.log 2>&1
log "done"
