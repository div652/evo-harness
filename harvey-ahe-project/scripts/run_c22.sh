#!/usr/bin/env bash
# Campaign 22: test campaign 21's winner. Waits for campaign 21 to finish,
# picks the checkpoint among C5-C10 with the highest all-pass on campaign 21
# (ties broken by task pass). If that is C5 there is nothing to run (C5 already
# has 3 trials on these 70 tasks). Otherwise the winner is evaluated 3 times on
# campaign 15's 70 test tasks, resumed after an infrastructure failure up to
# MAX_INVOCATIONS times; completed units are kept.
#
# Usage, inside tmux, from anywhere:  bash harvey-ahe-project/scripts/run_c22.sh
set -u
cd /home/agarwaldi/AHE_Harvey_cao
P=harvey-ahe-project
A=$P/campaign-artifacts
PY=/home/agarwaldi/AHE_Harvey/.venv/bin/python
MAX_INVOCATIONS=${MAX_INVOCATIONS:-6}
export CAO_API_KEY="$(cat /home/agarwaldi/cao/profile/.gateway-key)"
export PYTHONPATH=$PWD/src:$PWD/$P
log() { echo "[c22 $(date -u +%FT%TZ)] $*" | tee -a $A/c22-run.log; }
log "waiting for campaign 21"
until grep -q "all done" $A/c21-run.log; do sleep 60; done
log "campaign 21: $(grep 'all done' $A/c21-run.log | tail -1)"
W=$($PY -I - <<'PYEOF'
import json,glob,os
A='/home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project/campaign-artifacts/'
rows=[]
for c in ['C5','C6','C7','C8','C9','C10']:
    res=[]
    for u in glob.glob(A+f'harvey-lab-campaign-21-cao-c12val-{c}/evaluations/*/units/*'):
        best=None
        for a in sorted(glob.glob(u+'/attempt-*'),key=lambda x:int(x.rsplit('-',1)[1])):
            for g in sorted(glob.glob(a+'/grading/grading-*'),key=lambda x:int(x.rsplit('-',1)[1])):
                f=g+'/scores_judge-1.json'
                if os.path.exists(f): best=json.load(open(f))
        if best: res.append((best['all_pass'],best['n_passed']/best['n_criteria']))
    if len(res)!=40: raise SystemExit(f'{c} has {len(res)}/40 graded')
    rows.append((sum(r[0] for r in res)/40,sum(r[1] for r in res)/40,c))
rows.sort(reverse=True)
import sys
for r in rows: print(f'{r[2]} all-pass {r[0]:.3f} task {r[1]:.3f}',file=sys.stderr)
print(rows[0][2])
PYEOF
) 2>>$A/c22-run.log || { log "winner selection failed"; exit 1; }
log "winner: $W"
if [ "$W" = C5 ]; then log "C5 wins: nothing to run"; exit 0; fi
CFG=$P/ahe-cao-c22-test70-$W.yaml
sed "s/WINNER/$W/g" $P/ahe-cao-c22-test70-TEMPLATE.yaml > $CFG
$PY -c "from pathlib import Path; from ahe_runner.config import load_config; from pathlib import Path; load_config(Path('$CFG'))" || { log "config $CFG does not load"; exit 1; }
/home/agarwaldi/cao/cao.sh status | grep -q running || { log "CAO gateway not running"; exit 1; }
for i in $(seq 1 "$MAX_INVOCATIONS"); do
  log "$W invocation $i"
  $PY $P/scripts/run_c0_train_only.py --config $CFG >> $A/c22-$W-run.log 2>&1
  rc=$?; echo "EXIT=$rc" >> $A/c22-$W-run.log; log "$W invocation $i exit $rc"
  [ "$rc" -eq 0 ] && exit 0
  sleep 120
done
exit 1
