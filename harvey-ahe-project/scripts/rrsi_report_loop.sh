#!/usr/bin/env bash
# Refresh ~/rrsi-pilot/RRSI_FK_ROUNDS.md every 10 minutes while the RRSI
# campaign runs; one last refresh after it ends.
P=/home/agarwaldi/rrsi-pilot
gen() { python3 $P/harvey-ahe-project/scripts/rrsi_rounds_report.py $P/harvey-ahe-project/campaign-artifacts/rrsi-fk-cao-luna-80-40 $P/RRSI_FK_ROUNDS.md; }
while tmux has-session -t rrsi-fk 2>/dev/null; do gen; sleep 600; done
gen
