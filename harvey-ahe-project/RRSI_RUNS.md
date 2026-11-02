# RRSI on Harvey LAB

This branch holds the Harvey LAB integration for running the RRSI evolution
algorithm (`algorithm.name: rrsi`) with the runner on `main`. Everything here
is benchmark-specific and stays off `main`: the adapter port, the RRSI role
supplements, the splits, the campaign configurations, and the launchers.

## Contents

| Path | What it is |
|---|---|
| `harvey_ahe/` | The Harvey adapter from `harveybench-cao` (`158d762`), ported to the 0.9.0 runner: agent sessions carry `unit_id` and `attempt` (cost attribution), trial facts carry the criteria count as `weight` (RRSI's pooled score), an empty validation split is accepted, and harveybench-only runner symbols (evidence-only extra trials, `transport.provider`) are stubbed. |
| `rrsi_supplements_fk/` | RRSI role supplements for firm-knowledge tasks: RRSI's Harvey briefs for method, AHE's Harvey supplements for harness facts only. |
| `rrsi_supplements_lab/` | The same for general Harvey LAB tasks. |
| `splits-firm-knowledge-rrsi-80-0-40.json` | Firm-knowledge: train = campaign 23's 80; test = campaign 23's 20 test tasks + 20 of campaign 24's held-out 50. |
| `splits-rrsi-80-0-40.json` | General LAB: the RRSI paper's generator at LAB `1da4750` with 80 evolve tasks; test = the paper's 40 held-out tasks. |
| `ahe-rrsi-pilot.yaml`, `ahe-rrsi-fk-80-40.yaml` | Pilot and firm-knowledge campaign configurations (gpt-5.6-luna agent, one gpt-5.6-sol judge, gpt-5.6-sol meta agents, CAO gateway). |
| `scripts/run_rrsi_pilot.sh`, `scripts/run_rrsi_fk.sh` | Launchers (run, then resume after interruptions). They expect the project at `~/rrsi-pilot/harvey-ahe-project`. |

The other files are the `harveybench-cao` project as of `158d762`.

## Runs

The firm-knowledge campaign's runner commit is tagged `rrsi-fk-runner`
(`7470b27`); the pilot's runner, `1c99ffb`, is an ancestor of it.

### Pilot (10 training tasks, 2 rounds)

A two-round RRSI campaign ran end to end on 2026-10-27 through the CAO gateway:
gpt-5.6-luna agent, one gpt-5.6-sol judge, gpt-5.6-sol meta agents, the
firm-knowledge pilot split (10 training tasks, 1 test task), 2 trials, 2
variants per round, the runner frozen at `1c99ffb`, and the Harvey adapter
ported to this runner (session unit IDs, criteria as trial weights). It is a
pipeline check, not a result.

| Step | Outcome |
|---|---|
| C0 training, cost, calibration | S = 0.400; 20 of 20 trials priced (6.24 catalog units per trial); bootstrap delta = 0.378 |
| Round 0 | 33 digests; A (C1): S 0.392 at +202% cost, rejected; B (C2): S 0.583 at -4% cost, accepted |
| Round 1 | budget 2; A (C3): S 0.475, rejected; B (C4): S 0.683 at -19% cost, accepted |
| Selection, final test | algorithm policy, C4; test (1 task x 2 trials) C0 0.590, C4 0.603 |

Two `podman info` timeouts interrupted evaluations; each resume retried only
the affected trial and reused every completed stage. The critic accepted every
candidate on its first review, and the tag check re-tagged two edits to an
existing tool from `client_tool` to `control_flow`.

The pilot's noise band is large because these tasks have 2 to 24 criteria and
trials of the same task often disagree, so both accepted gains are inside it.
With 80 tasks and 3 trials, the firm-knowledge campaign below measured
delta = 0.048.

### Firm-knowledge campaign (80 train / 40 test)

Launched 2026-11-02 02:02 IST: `ahe-rrsi-fk-80-40.yaml`, 20 rounds, 2
variants, 3 training trials, 3 test trials. Calibrated noise band delta =
0.048. In progress at the time of writing.
