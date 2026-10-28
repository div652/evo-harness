"""Run-level statistics of a stage-harness evaluation (stages, reviews, reopens) by outcome."""
import collections, glob, json, re, statistics as st, sys

E = sys.argv[1]
runs = []
for u in glob.glob(E + '/units/*'):
    try:
        a = sorted(glob.glob(u + '/attempt-*'), key=lambda p: int(p.rsplit('-', 1)[1]))[-1]
        un = json.load(open(u + '/unit.json'))
        sc = json.load(open(sorted(glob.glob(a + '/grading/*/scores_judge-1.json'))[-1]))
        res = json.load(open(a + '/result.json'))
    except Exception:
        continue
    uses, names, steps = [], {}, []
    for l in open(a + '/trace.jsonl'):
        e = json.loads(l)
        if e.get('event_type') != 'message' or isinstance(e['message'], str):
            continue
        for c in e['message'].get('content', []):
            if c.get('type') == 'tool_use':
                names[c['id']] = (c['name'], c['input']); uses.append((c['name'], c['input']))
            elif c.get('type') == 'tool_result' and names.get(c.get('tool_use_id'), ('',))[0] == 'stage_end':
                x = json.dumps(c.get('content'))
                v = re.search(r'Independent reviewer: goal reached = (\w+)', x)
                steps.append({'critic': v.group(1) if v else 'n/a', 'self': names[c['tool_use_id']][1].get('goal_reached')})
    starts = [i.get('stage') for n, i in uses if n == 'stage_start']
    # did the agent reopen the same stage right after each review?
    for k, s in enumerate(steps):
        s['reopen'] = k + 1 < len(starts) and starts[k + 1] == starts[k]
    term = res.get('termination_reason') or res.get('native_result', {}).get('termination_reason')
    runs.append({'task': un['task_id'][-3:], 'pass': sc['all_pass'], 'calls': len(uses), 'starts': starts,
                 'reviews': steps, 'term': term})
P = [r for r in runs if r['pass']]; F = [r for r in runs if not r['pass']]
print(f"runs {len(runs)}: pass {len(P)} fail {len(F)}")
for lab, R in (('pass', P), ('fail', F)):
    rv = [s for r in R for s in r['reviews']]
    c = collections.Counter(s['critic'] for s in rv)
    moved = collections.Counter(s['critic'] for s in rv if not s['reopen'])
    print(f"[{lab}] calls/run {st.mean(r['calls'] for r in R):.0f}  stages/run {st.mean(len(r['starts']) for r in R):.1f}  "
          f"reopens/run {st.mean(sum(s['reopen'] for s in r['reviews']) for r in R):.1f}  context_overflow {sum(r['term']=='context_overflow' for r in R)}")
    print(f"   critic verdicts {dict(c)}; moved on despite critic 'no' {moved['no']}/{c['no']}, 'partly' {moved['partly']}/{c['partly']}")
    print(f"   agent self 'not reached' {sum(1 for s in rv if s['self'] is False)}/{len(rv)}")
    last = collections.Counter(r['reviews'][-1]['critic'] if r['reviews'] else 'none' for r in R)
    print(f"   critic verdict on the LAST stage before finish: {dict(last)}")
stg = sorted({s for r in runs for s in r['starts']})
print("\nstage -> share of runs using it (pass / fail)")
for s in stg:
    print(f"  {s:48s} {sum(s in r['starts'] for r in P)/len(P):4.0%} {sum(s in r['starts'] for r in F)/len(F):4.0%}")
