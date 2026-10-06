# Corrector re-review: LDTT Stamp Spec v0.1.1
Date: 2026-10-06 · Reviewer: LDTT Corrector
Files: LDTT-Stamp-Spec-v0.1.1.md, schema/ldtt.schema.json (+ test_schema.py), examples/ldtt.observe.example.yaml, templates/LDTT-Evidence-Checklist-v0.1.1.md, LDTT-Phase2-Handoff.md
Probe script: reviews/v0.1.1-schema-probe.py (run with a Python that has pyyaml + jsonschema, e.g. /workspace/.venv-ldtt/bin/python)

## Verdict: FAIL (one item, narrow)
D1, D2 and F1–F7 are all closed correctly. §9 lock (incl. no time expiry, expires_at reserved/omitted) is applied. Brand is clean (Linked Drone Tool Trust, no HALO/old name anywhere), connector-only, no FAA/aircraft claims, phase order and $0 hold. test_schema.py: 11/11 pass; §4 example validates.

It fails on D3: the schema still lets a manifest move the vehicle or write params through paths that skip command_allowlist and param_allowlist. All cases below validate as VALID against ldtt.schema.json today:

## DRIFT
- D3 (levels/controls coherence; same class as D1). Write/motion bypass paths:
  a. tx_allowlist is not constrained by level. Observe can list PARAM_SET, MISSION_ITEM_INT, COMMAND_LONG. Operate can list RC_CHANNELS_OVERRIDE, MANUAL_CONTROL, SET_POSITION_TARGET_LOCAL_NED, SET_MODE, i.e. fly the aircraft without any MAV_CMD.
  b. PARAM_SET in tx_allowlist without operate:params, so param_allowlist (and the §2.1 denylist) never applies.
  c. At Command, MAV_CMD_DO_SET_PARAMETER and MAV_CMD_PREFLIGHT_STORAGE (param reset) are allowed. Both bypass param_allowlist and can hit protected settings.
  d. The Operate camera/payload pattern includes MAV_CMD_DO_SET_ROI*, which yaws multicopters toward the ROI. That's vehicle motion at Operate.
  FIX:
  - Observe tx_allowlist: read-only message set only (HEARTBEAT, REQUEST_DATA_STREAM, PARAM_REQUEST_READ/LIST, MISSION_REQUEST_LIST/INT, MISSION_ACK, LOG_REQUEST_LIST/DATA/END; COMMAND_LONG only for the read commands in F8).
  - Operate tx_allowlist: deny motion messages (SET_MODE, MANUAL_CONTROL, RC_CHANNELS_OVERRIDE, SET_POSITION_TARGET_LOCAL_NED, SET_POSITION_TARGET_GLOBAL_INT, SET_ATTITUDE_TARGET, SET_ACTUATOR_CONTROL_TARGET).
  - PARAM_SET in tx_allowlist requires operate:params + param_allowlist.
  - Add MAV_CMD_DO_SET_PARAMETER and MAV_CMD_PREFLIGHT_STORAGE to protectedCmd for v0.1.
  - Drop DO_SET_ROI from cameraPayloadCmd; ROI is Command (command:reposition) in v0.1.
  - Add each case as a negative test in test_schema.py. Spec text: one line in §4 level rules saying tx_allowlist is level-limited.

## FIX
- F8 Observe can't use MAV_CMD_REQUEST_MESSAGE or MAV_CMD_SET_MESSAGE_INTERVAL (command_allowlist must be empty). These are the standard read requests; PX4 largely ignores REQUEST_DATA_STREAM. Change the Observe rule from "empty" to "read-only request commands only" (those two).
- F9 §2.1 item 4 names Remote ID, but the schema denylist has no Remote ID params. Add ArduPilot DID_* now (PX4 COM_ARM_ODID is already covered by COM_ARM_.*). Full list stays Phase 2.
- F10 At Observe, MCP tools can carry operate:/command: scopes (validated VALID). Restrict tool scopes to the level, same as top-level scopes; "tool scope is listed in scopes" can be a review check.
- F11 (optional) Schema allows level: command with only observe scopes. Spec says level = highest declared scope; enforce or note as review check.

## PLAN REF
- P1 Phase 2 mapping table should cover tx messages to scopes, not just MAV_CMDs (feeds D3 lists).
- P2 Handoff note is fine for Phase 2 once D3/F8 land; Observe reference connector should use F8's request commands if it targets PX4 as well as ArduPilot SITL.

## Not drift
Brand, scope, non-goals, FAA wording, HALO removal, $0, phase order, §9 decisions, stamp record and revocation list formats, evidence template, handoff scope.
