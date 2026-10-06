import json,yaml,jsonschema,copy
s=json.load(open('schema/ldtt.schema.json'))
ex=yaml.safe_load(open('examples/ldtt.observe.example.yaml'))
v=jsonschema.Draft202012Validator(s)
def chk(name,m):
    errs=list(v.iter_errors(m)); print(name,'->', 'VALID' if not errs else 'invalid: '+errs[0].message[:90])
chk('example',ex)
m=copy.deepcopy(ex); m['transport']['mavlink']['tx_allowlist']+=['PARAM_SET','COMMAND_LONG','MISSION_ITEM_INT']; chk('observe tx PARAM_SET/COMMAND_LONG/MISSION_ITEM_INT',m)
op=copy.deepcopy(ex); op['level']='operate'; op['scopes']=['observe:telemetry','operate:payload']; op['heartbeat']={'interval_s':1,'timeout_s':5,'on_timeout':'halt_writes'}; op['operator_confirmation']={'required_for':['operate:*'],'ui':'x'}; op['audit_log']['includes']+=['write','confirmation','result']
m=copy.deepcopy(op); m['transport']['mavlink']['tx_allowlist']+=['RC_CHANNELS_OVERRIDE','SET_POSITION_TARGET_LOCAL_NED','MANUAL_CONTROL','SET_MODE']; chk('operate tx motion msgs',m)
m=copy.deepcopy(op); m['transport']['mavlink']['command_allowlist']=['MAV_CMD_DO_SET_ROI_LOCATION']; chk('operate DO_SET_ROI_LOCATION',m)
m=copy.deepcopy(op); m['transport']['mavlink']['tx_allowlist']+=['PARAM_SET']; chk('operate PARAM_SET w/o operate:params',m)
m=copy.deepcopy(op); m['scopes'].append('operate:params'); m['transport']['mavlink']['param_allowlist']=['DID_ENABLE']; chk('operate param_allowlist DID_ENABLE',m)
cm=copy.deepcopy(op); cm['level']='command'; cm['audit_log']['includes'].append('command'); cm['transport']['mavlink']['signing']=True
m=copy.deepcopy(cm); m['transport']['mavlink']['command_allowlist']=['MAV_CMD_DO_SET_PARAMETER','MAV_CMD_PREFLIGHT_STORAGE']; chk('command DO_SET_PARAMETER/PREFLIGHT_STORAGE',m)
m=copy.deepcopy(ex); m['transport']={'kind':'mcp','mcp':{'tools':[{'name':'t','scope':'operate:mission','writes':False}]}}; chk('observe mcp tool w/ operate scope',m)
m=copy.deepcopy(ex); m['transport']['mavlink']['command_allowlist']=['MAV_CMD_SET_MESSAGE_INTERVAL']; chk('observe SET_MESSAGE_INTERVAL',m)
