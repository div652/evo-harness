"""Compact view of one stage-harness trace: each call with short args and result."""
import json, sys
W = int(sys.argv[2]) if len(sys.argv) > 2 else 220
for l in open(sys.argv[1]):
    e = json.loads(l)
    if e.get('event_type') != 'message' or isinstance(e['message'], str):
        continue
    m = e['message']; i = e['index']
    for c in m.get('content', []):
        t = c.get('type')
        if t == 'text' and str(i) != '0':
            print(f"[{i} {m.get('role')}] TEXT {c['text'][:W*3]!r}")
        elif t == 'tool_use':
            a = c['input']
            if c['name'] in ('stage_start', 'stage_end'):
                print(f"[{i}] ### {c['name']} {json.dumps(a, ensure_ascii=False)[:W*4]}")
            else:
                print(f"[{i}] CALL {c['name']} {json.dumps(a, ensure_ascii=False)[:W]}")
        elif t == 'tool_result':
            x = c.get('content'); x = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
            x = x.replace('\\n', ' | ')
            if '[Stage review' in x:
                k = x.find('Independent reviewer'); print(f"[{i}]   -> REVIEW {x[k:k+W*3]}")
            else:
                print(f"[{i}]   -> {len(x)}ch {x[:W]}")
