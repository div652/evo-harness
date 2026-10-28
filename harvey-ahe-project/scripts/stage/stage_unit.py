# Offline unit test of the stage-protocol harness (harness_stage): fake agent state,
# real critic/fit calls via CAO. Run: /home/agarwaldi/AHE_Harvey/.venv/bin/python harvey-ahe-project/scripts/stage/stage_unit.py
import os, sys, types
os.environ['CAO_API_KEY']=open('/home/agarwaldi/cao/profile/.gateway-key').read().strip()
sys.path.insert(0, '/home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project/harness_stage')
from middleware.stage_guard import StageGuardMiddleware
from tools.stage import stage_start, stage_end
from nexau.core.messages import Message, Role, TextBlock
class S:
    def __init__(s): s.g={}
    def get_global_value(s,k,d=None): return s.g.get(k,d)
    def set_global_value(s,k,v): s.g[k]=v
st=S(); mw=StageGuardMiddleware()
P=lambda n,a,i='x': types.SimpleNamespace(tool_name=n,parameters=a,tool_call_id=i,agent_state=st)
def run(n,a,i='x',out='OK'):
    def nxt(p):
        if n=='stage_start': return stage_start(agent_state=st,**a)
        if n=='stage_end': return stage_end(agent_state=st,**a)
        return out
    return mw.wrap_tool_call(P(n,a,i),nxt)
mw.before_model(types.SimpleNamespace(agent_state=st,messages=[Message(role=Role.USER,content=[TextBlock(text='Which matters involved a signed supply agreement? Cite the proof documents.')])]))
print('1', run('glob',{'pattern':'**/*'}))
print('2', run('stage_start',{'stage':'Search file contents for request keywords','goal':'find all candidate matters mentioning a supply agreement'}))
print('3', run('stage_start',{'stage':'Screen candidate matters by reading documents','goal':'x'}))
print('4', run('finish',{'summary':'s'}))
r=run('grep',{'pattern':'supply agreement','path':'documents'},out={'result':'Grep page: shown=3\nmatters/1099-00001/a.eml\nmatters/1099-00002/b.eml\nmatters/1099-00003/c.eml'}); print('5', r)
r=run('write',{'file_path':'output/response.md','content':'draft'}); print('6', r)
print('7 state surfaced/opened', st.g['harvey_stage_state_v1']['surfaced'], st.g['harvey_stage_state_v1']['opened'])
# mixed batch
call=lambda n,i: types.SimpleNamespace(tool_name=n,tool_call_id=i)
mw.after_model(types.SimpleNamespace(agent_state=st,parsed_response=types.SimpleNamespace(tool_calls=[call('stage_end','a'),call('read','b')]),messages=[]))
print('8', run('stage_end',{'goal_reached':True,'summary':'s'},i='a')); print('8b', run('read',{'file_path':'x'},i='b'))
r9=run('stage_end',{'goal_reached':True,'summary':'Ran one grep; 3 matters surfaced; did not try other searches.'}); print('9', r9); print('9b search-stage review lists unopened:', 'appeared in your search results' in r9)
res=mw.after_model(types.SimpleNamespace(agent_state=st,parsed_response=types.SimpleNamespace(tool_calls=[]),messages=[]))
print('10 force_continue', res.force_continue, res.messages[-1].content[0].text[:120])
print('11', run('stage_start',{'stage':'new','goal':'g'}))
print('12', run('stage_start',{'stage':'new','goal':'map client names to matters','new_stage_name':'Map clients to matters'}))
# Surfaced-not-opened list: shown only at stages where training placed that error.
run('stage_end',{'goal_reached':True,'summary':'x'})
print('14', run('stage_start',{'stage':'Screen candidate matters by reading documents','goal':'open every candidate'})[:60])
run('read',{'file_path':'documents/matters/1099-00001/a.docx'})
r=run('stage_end',{'goal_reached':True,'summary':'Opened one of three candidates.'})
print('15 screen review lists unopened:', [l for l in r.splitlines() if 'appeared in your search' in l])
