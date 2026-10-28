import json,sys,glob,os
d=sys.argv[1]; W=int(sys.argv[2]) if len(sys.argv)>2 else 250
calls=sorted(glob.glob(d+'/attempt-*/model_calls/call-*/request.json'))
r=json.load(open(calls[-1]))['kwargs']; print('calls',len(calls))
items=r.get('input') or r.get('messages') or []
for it in items[1:]:
    t=it.get('type') or it.get('role')
    if t=='function_call': print('CALL',it.get('name'),it.get('arguments','')[:W])
    elif t=='function_call_output': print('  ->',str(it.get('output',''))[:W].replace('\n',' | '))
    else:
        c=it.get('content'); c=' '.join(x.get('text','') for x in c if isinstance(x,dict)) if isinstance(c,list) else str(c)
        print(t, c[:W].replace('\n',' | '))
