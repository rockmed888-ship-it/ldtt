import json,yaml,jsonschema,copy
s=json.load(open('schema/ldtt.schema.json'))
ex=yaml.safe_load(open('examples/ldtt.observe.example.yaml'))
v=jsonschema.Draft202012Validator(s)
def chk(name,m):
    errs=list(v.iter_errors(m)); print(name,'->', 'VALID' if not errs else 'invalid: '+errs[0].message[:90])
chk('example',ex)
op=copy.deepcopy(ex); op['level']='operate'; op['scopes']=['observe:telemetry','operate:payload']; op['heartbeat']={'interval_s':1,'timeout_s':5,'on_timeout':'halt_writes'}; op['operator_confirmation']={'required_for':['operate:*'],'ui':'x'}; op['audit_log']['includes']+=['write','confirmation','result']
op['transport']['mavlink']['command_allowlist']=['MAV_CMD_IMAGE_START_CAPTURE']
chk('operate base',op)
for msg in ['GPS_INPUT','HIL_GPS','VISION_POSITION_ESTIMATE','FOLLOW_TARGET','LANDING_TARGET','MISSION_SET_CURRENT','SET_GPS_GLOBAL_ORIGIN','SET_HOME_POSITION','MANUAL_SETPOINT','ODOMETRY','COMMAND_INT']:
    m=copy.deepcopy(op); m['transport']['mavlink']['tx_allowlist'].append(msg); chk('operate tx '+msg,m)
cm=copy.deepcopy(op); cm['level']='command'; cm['scopes'].append('command:mode'); cm['audit_log']['includes'].append('command'); cm['transport']['mavlink']['signing']=True
for c in ['MAV_CMD_DO_FLIGHTTERMINATION','MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN','MAV_CMD_DO_MOTOR_TEST']:
    m=copy.deepcopy(cm); m['transport']['mavlink']['command_allowlist']=[c]; chk('command '+c,m)
