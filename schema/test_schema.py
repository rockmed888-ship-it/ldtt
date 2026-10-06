# Run: python schema/test_schema.py  (needs jsonschema, pyyaml). Checks the example and every level rule.
import os, json, copy, yaml, jsonschema
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
S = json.load(open('schema/ldtt.schema.json'))
jsonschema.Draft202012Validator.check_schema(S)
V = jsonschema.Draft202012Validator(S)
base = yaml.safe_load(open('examples/ldtt.observe.example.yaml'))
fails = 0
def check(name, doc, expect):
    global fails
    errs = list(V.iter_errors(doc)); ok = not errs
    if ok != expect: fails += 1
    print(('PASS' if ok == expect else 'WRONG'), name, '->', 'valid' if ok else 'invalid: ' + errs[0].message[:80])
def mav(d): return d['transport']['mavlink']

# Observe
check('observe example', base, True)
d = copy.deepcopy(base); d['rate_limits']['writes_per_min'] = 5; check('observe writes>0', d, False)
d = copy.deepcopy(base); mav(d)['command_allowlist'] = ['MAV_CMD_NAV_TAKEOFF']; check('observe motion command', d, False)
d = copy.deepcopy(base); mav(d)['command_allowlist'] = ['MAV_CMD_SET_MESSAGE_INTERVAL']; check('F8 observe SET_MESSAGE_INTERVAL', d, True)
d = copy.deepcopy(base); mav(d)['command_allowlist'] = ['MAV_CMD_REQUEST_MESSAGE']; check('F8 observe REQUEST_MESSAGE', d, True)
for m in ['PARAM_SET', 'MISSION_ITEM_INT', 'MISSION_COUNT', 'RC_CHANNELS_OVERRIDE', 'SET_MODE']:
    d = copy.deepcopy(base); mav(d)['tx_allowlist'].append(m); check('D3 observe tx ' + m, d, False)
d = copy.deepcopy(base); d['privacy']['egress'] = [{'destination': 'x', 'data': ['telemetry'], 'purpose': 'p'}]; d['privacy'].pop('egress_runtime_opt_in'); check('egress no opt-in', d, False)
d['privacy']['egress_runtime_opt_in'] = True; check('egress with opt-in', d, True)
d = copy.deepcopy(base); d['transport'] = {'kind': 'mcp', 'mcp': {'tools': [{'name': 't', 'scope': 'operate:mission', 'writes': False}]}}; check('F10 observe mcp tool operate scope', d, False)
d = copy.deepcopy(base); d['transport'] = {'kind': 'mcp', 'mcp': {'tools': [{'name': 't', 'scope': 'observe:telemetry', 'writes': False}]}}; check('observe mcp tool observe scope', d, True)

# v0.1.4 revocation list_url sources
for u, exp in [('https://example.org/r.json', True), ('file:///opt/ldtt/revocations.json', True), ('placeholders/revocations/revocations.json', True), ('./revocations.json', True),
               ('http://example.org/r.json', False), ('ftp://example.org/r.json', False), ('/abs/path/r.json', False), ('', False)]:
    d = copy.deepcopy(base); d['revocation']['list_url'] = u; check('S1 list_url ' + (u or '<empty>'), d, exp)
d = copy.deepcopy(base); d['ldtt_spec'] = '0.1.3'; check('S1 ldtt_spec 0.1.3 still accepted', d, True)
d = copy.deepcopy(base); d['ldtt_spec'] = '0.1.2'; check('S1 ldtt_spec 0.1.2 rejected', d, False)

# Operate
op = copy.deepcopy(base); op['level'] = 'operate'; op['scopes'] = ['observe:telemetry', 'operate:payload']
op['heartbeat'] = {'interval_s': 1, 'timeout_s': 5, 'on_timeout': 'halt_writes'}
op['operator_confirmation'] = {'required_for': ['operate:*'], 'ui': 'dialog'}
op['audit_log']['includes'] += ['write', 'confirmation', 'result']
mav(op)['command_allowlist'] = ['MAV_CMD_IMAGE_START_CAPTURE', 'MAV_CMD_REQUEST_MESSAGE']
check('operate valid', op, True)
for m in ['RC_CHANNELS_OVERRIDE', 'MANUAL_CONTROL', 'SET_POSITION_TARGET_LOCAL_NED', 'SET_POSITION_TARGET_GLOBAL_INT', 'SET_ATTITUDE_TARGET', 'SET_ACTUATOR_CONTROL_TARGET', 'SET_MODE']:
    d = copy.deepcopy(op); mav(d)['tx_allowlist'].append(m); check('D3 operate tx ' + m, d, False)
d = copy.deepcopy(op); mav(d)['tx_allowlist'] += ['MISSION_COUNT', 'MISSION_ITEM_INT']; d['scopes'].append('operate:mission'); check('operate mission upload msgs', d, True)
d = copy.deepcopy(op); mav(d)['tx_allowlist'] += ['MISSION_COUNT', 'MISSION_ITEM_INT', 'MISSION_CLEAR_ALL', 'MISSION_WRITE_PARTIAL_LIST', 'COMMAND_INT', 'GIMBAL_MANAGER_SET_ATTITUDE', 'GIMBAL_MANAGER_SET_PITCHYAW']; d['scopes'].append('operate:mission'); check('D3-r operate full tx allowlist', d, True)
for m in ['GPS_INPUT', 'HIL_GPS', 'VISION_POSITION_ESTIMATE', 'ODOMETRY', 'SET_GPS_GLOBAL_ORIGIN', 'FOLLOW_TARGET', 'LANDING_TARGET', 'MISSION_SET_CURRENT', 'MANUAL_SETPOINT', 'SET_HOME_POSITION']:
    d = copy.deepcopy(op); mav(d)['tx_allowlist'].append(m); check('D3-r operate tx ' + m, d, False)
for c in ['MAV_CMD_DO_SET_ROI_LOCATION', 'MAV_CMD_DO_SET_ROI', 'MAV_CMD_NAV_TAKEOFF']:
    d = copy.deepcopy(op); mav(d)['command_allowlist'] = [c]; check('D3 operate cmd ' + c, d, False)
d = copy.deepcopy(op); mav(d)['tx_allowlist'].append('PARAM_SET'); check('D3 operate PARAM_SET without operate:params', d, False)
d = copy.deepcopy(op); mav(d)['tx_allowlist'].append('PARAM_SET'); d['scopes'].append('operate:params'); check('D3 operate PARAM_SET without param_allowlist', d, False)
d = copy.deepcopy(op); mav(d)['tx_allowlist'].append('PARAM_SET'); d['scopes'].append('operate:params'); mav(d)['param_allowlist'] = ['CAM1_TYPE']; check('operate PARAM_SET with params scope + allowlist', d, True)
d = copy.deepcopy(op); d['scopes'].append('operate:params'); mav(d)['param_allowlist'] = ['CAM1_TYPE']; check('operate params valid', d, True)
for prm in ['FENCE_ENABLE', 'FS_THR_ENABLE', 'ARMING_CHECK', 'DID_ENABLE', 'COM_ARM_ODID']:
    d = copy.deepcopy(op); d['scopes'].append('operate:params'); mav(d)['param_allowlist'] = [prm]; check('protected param ' + prm, d, False)
d = copy.deepcopy(op); d['scopes'] = ['observe:telemetry']; check('F11 operate with only observe scopes', d, False)
d = copy.deepcopy(op); d['scopes'].append('command:arm'); check('F11 operate with command scope', d, False)
d = copy.deepcopy(op); d['transport'] = {'kind': 'mcp', 'mcp': {'tools': [{'name': 't', 'scope': 'command:arm', 'writes': True}]}}; check('F10 operate mcp tool command scope', d, False)

# Command
c = copy.deepcopy(op); c['level'] = 'command'; c['scopes'].append('command:arm'); c['audit_log']['includes'].append('command')
mav(c)['command_allowlist'] = ['MAV_CMD_COMPONENT_ARM_DISARM']
check('command no signing', c, False)
mav(c)['signing'] = True; check('command signed', c, True)
d = copy.deepcopy(c); mav(d)['tx_allowlist'].append('SET_POSITION_TARGET_GLOBAL_INT'); mav(d)['command_allowlist'].append('MAV_CMD_DO_SET_ROI_LOCATION'); check('command motion msg + ROI', d, True)
d = copy.deepcopy(c); mav(d)['tx_allowlist'] += ['GPS_INPUT', 'MISSION_SET_CURRENT', 'SET_HOME_POSITION']; check('command may send non-Operate msgs', d, True)
for pc in ['MAV_CMD_DO_FENCE_ENABLE', 'MAV_CMD_DO_SET_PARAMETER', 'MAV_CMD_PREFLIGHT_STORAGE']:
    d = copy.deepcopy(c); mav(d)['command_allowlist'].append(pc); check('D3 command protected ' + pc, d, False)
d = copy.deepcopy(c); d['scopes'] = ['observe:telemetry', 'operate:payload']; check('F11 command with no command scope', d, False)

print('\nFAILURES:', fails)
raise SystemExit(1 if fails else 0)
