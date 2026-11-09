#!/usr/bin/env bash
# Judge the reviewer-swap arms (reviewer-independent: does the review raise the first error, does the next step commit to fixing it).
set -u
cd /home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
D=analysis/feedback-replay; L=$D/logs
log() { echo "[$(TZ=Asia/Kolkata date +%F' '%T) IST] $*" | tee -a $L/run_reviewer_swap.log; }
# wait for both sonnet replay jobs to end (their logs stop growing and no sonnet process remains)
while pgrep -f "reviewer_swap.py --round r[23] --reviewer sonnet" >/dev/null; do sleep 20; done
log "judging original, control_nosum, reviewer_sonnet (12 workers)"
for a in original control_nosum reviewer_sonnet; do python3 $D/judge_problem.py --arm $a --workers 12 >> $L/judge_problem_$a.log 2>&1; done
while pgrep -f "reviewer_swap.py --round r[23] --reviewer luna" >/dev/null; do sleep 20; done
log "judging reviewer_luna (24 workers)"
python3 $D/judge_problem.py --arm reviewer_luna --workers 24 >> $L/judge_problem_reviewer_luna.log 2>&1
for a in original control_nosum reviewer_sonnet reviewer_luna; do python3 $D/judge_problem.py --arm $a --workers 8 >> $L/judge_problem_$a.log 2>&1; done  # fill any gaps
python3 $D/judge_problem.py --summarize original control_nosum reviewer_sonnet reviewer_luna >> $L/judge_problem_summary.log 2>&1
log "judging done"
