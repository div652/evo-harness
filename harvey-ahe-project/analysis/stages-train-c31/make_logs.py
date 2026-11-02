"""Build compact per-run call logs for stage annotation.

One file per round-3 stage-harness (harness_stage_r3) training run of campaign 31 (80 tasks x 3). Stage
calls (stage_start / stage_end) are logged with their arguments; their results
are shortened to the critic's verdict, flags and recommendation, and never
carry target-matter markers (the harness's own feedback lists matter numbers).
logs/<task>_T<trial>.txt with the request, the rubric verdicts, and one line
per tool call / result, plus which rubric matter numbers each result surfaced.
"""
import glob, json, os, re, sys
ROOT = '/home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project/campaign-artifacts'
SRC = [f'{ROOT}/harvey-lab-campaign-31-cao-stage-r3-train80/evaluations/C0-train']
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
MAT = re.compile(r'\b\d{4}-\d{5}\b')

def short(s, n):
    s = s.replace('\\n', ' | ').replace('\n', ' | ')
    return s if len(s) <= n else s[:n] + f'…(+{len(s)-n})'

def latest(u):
    a = sorted(glob.glob(u + '/attempt-*'), key=lambda p: int(p.rsplit('-', 1)[1]))
    return a[-1] if a else None

index = []
for src in SRC:
    for u in sorted(glob.glob(src + '/units/*')):
        at = latest(u)
        if not at or not os.path.exists(at + '/trace.jsonl'):
            continue
        unit = json.load(open(u + '/unit.json'))
        task = unit['task_id'].rsplit('/', 1)[1]
        sj = sorted(glob.glob(at + '/grading/*/scores_judge-1.json'))
        if not sj:
            continue
        sc = json.load(open(sj[-1]))
        crit = sc['criteria_results']
        targets = sorted({m for c in crit for m in MAT.findall(c.get('title', ''))})
        L = []
        L.append(f"# task {task} trial T{unit['trial']}  unit {unit['unit_id']}")
        L.append(f"# source: {at}/trace.jsonl")
        L.append(f"# judge: {sc['n_passed']}/{sc['n_criteria']} passed, all_pass={sc['all_pass']}")
        L.append(f"# rubric matter numbers (target matters): {', '.join(targets) or 'none named'}")
        for c in crit:
            L.append(f"#   {c['id']} [{c['verdict']}] {c.get('title','')} :: {short(c.get('reasoning',''), 260)}")
        seen = set(); names = {}
        for line in open(at + '/trace.jsonl'):
            e = json.loads(line)
            if e.get('event_type') != 'message' or isinstance(e['message'], str):
                continue
            m = e['message']; idx = e['index']
            if str(idx) == '0':
                continue
            for c in m.get('content', []):
                t = c.get('type')
                if t == 'text':
                    n = 1500 if m.get('role') == 'user' else 400
                    L.append(f"[{idx} {m.get('role')}] TEXT: {short(c['text'], n)}")
                elif t == 'tool_use':
                    names[c.get('id')] = c['name']
                    inp = dict(c['input'])
                    if c['name'] in ('write', 'edit'):
                        for k in ('content', 'new_string', 'old_string'):
                            if k in inp:
                                inp[k] = short(str(inp[k]), 900 if k != 'old_string' else 150)
                    L.append(f"[{idx}] CALL {c['name']} {short(json.dumps(inp, ensure_ascii=False), 1400)}")
                elif t == 'tool_result':
                    x = c.get('content'); x = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
                    tool = names.get(c.get('tool_use_id'))
                    if tool in ('stage_start', 'stage_end'):
                        body = x.replace('\\n', '\n')
                        keep = [l for l in body.split('\n') if re.match(r'\s*(\"result\": \"\[Stage review|You reported|Independent reviewer|Reviewer flags|Reviewer recommendation|Stage started)', l) or l.startswith(('Independent reviewer','Reviewer flags','Reviewer recommendation','You reported','Stage started','[Stage review'))]
                        if tool == 'stage_start':
                            m0 = re.search(r'(Stage started: [^\n]*|\[Stage protocol\][^\n]*|Unknown stage[^\n]*)', body)
                            keep = [m0.group(1)] if m0 else [short(body, 200)]
                            keep += re.findall(r'Check the label:[^\n]*', body)
                        if tool == 'stage_end':
                            # Round-3 harness lines the annotators need: label note, suggested new step,
                            # and the list of entities seen but never opened (kept in full).
                            keep += [l for l in body.split('\n') if l.startswith(('Label: these calls', 'Reviewer suggests a new step', 'This stage has been opened'))]
                            sno = [l for l in body.split('\n') if 'appeared in your search results but none of whose documents' in l]
                        else:
                            sno = []
                        L.append(f"[{idx}]   -> {tool} result: {short(' | '.join(k.strip() for k in keep), 1400)}" + (f" | {sno[0].strip()}" if sno else ''))
                        continue
                    hit = [mm for mm in targets if mm in x]
                    new = [mm for mm in hit if mm not in seen]; seen |= set(hit)
                    tag = f"  <<target matter in result: {','.join(hit)}{' (FIRST TIME)' if new else ''}>>" if hit else ''
                    L.append(f"[{idx}]   -> {len(x)} chars: {short(x, 220)}{tag}")
        name = f"{task}_T{unit['trial']}.txt"
        open(os.path.join(OUT, name), 'w').write('\n'.join(L) + '\n')
        index.append({'task': task, 'trial': unit['trial'], 'all_pass': sc['all_pass'],
                      'n_passed': sc['n_passed'], 'n_criteria': sc['n_criteria'], 'log': f'logs/{name}'})
json.dump(sorted(index, key=lambda r: (r['task'], r['trial'])),
          open(os.path.join(os.path.dirname(OUT), 'runs_index.json'), 'w'), indent=1)
print(len(index), 'runs')
