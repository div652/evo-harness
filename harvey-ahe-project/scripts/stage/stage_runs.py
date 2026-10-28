import json,glob,sys,collections,re
E=sys.argv[1]
for u in sorted(glob.glob(E+'/units/*')):
    a=sorted(glob.glob(u+'/attempt-*'),key=lambda p:int(p.rsplit('-',1)[1]))[-1]
    un=json.load(open(u+'/unit.json')); sj=sorted(glob.glob(a+'/grading/*/scores_judge-1.json'))
    sc=json.load(open(sj[-1])) if sj else {}
    res=json.load(open(a+'/result.json')) if glob.glob(a+'/result.json') else {}
    ev=[];
    for l in open(a+'/trace.jsonl'):
        e=json.loads(l)
        if e.get('event_type')!='message' or isinstance(e['message'],str): continue
        for c in e['message'].get('content',[]):
            if c.get('type')=='tool_use': ev.append(('use',c['name'],c['input'],c.get('id')))
            elif c.get('type')=='tool_result': ev.append(('res',json.dumps(c.get('content'))))
    uses=[x for x in ev if x[0]=='use']; ress=[x[1] for x in ev if x[0]=='res']
    starts=[(x[2].get('stage'),x[2].get('new_stage_name')) for x in uses if x[1]=='stage_start']
    tn=collections.Counter(x[1] for x in uses)
    refused=sum('[Stage protocol]' in r and '"status": "error"' in r for r in ress)
    refused=sum(1 for r in ress if '[Stage protocol]' in r and ('No stage is open' in r or 'still open' in r or 'alone in their own turn' in r))
    notes=sum(1 for r in ress if 'Stage check:' in r)
    reviews=[r for r in ress if '[Stage review' in r]
    crit_ok=sum('Independent reviewer: goal reached' in r for r in reviews)
    reopen=sum('reopening this stage' in r for r in ress)
    print(f"task {un['task_id'][-3:]} T{un['trial']}: judge {sc.get('n_passed')}/{sc.get('n_criteria')} all_pass={sc.get('all_pass')} term={res.get('termination_reason', res.get('native_result',{}).get('termination_reason','?'))}")
    print(f"   calls {len(uses)} {dict(tn)}; stages {len(starts)} reopened {reopen}; refused {refused}; fit-notes {notes}; reviews {len(reviews)} critic-ok {crit_ok}")
    print('   seq:', ' → '.join((s if s!='new' else 'NEW:'+str(n)) for s,n in starts))
