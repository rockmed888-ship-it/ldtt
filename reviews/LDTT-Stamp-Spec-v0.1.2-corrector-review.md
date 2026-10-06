# Corrector re-review: LDTT Stamp Spec v0.1.2
Date: 2026-10-06 · Reviewer: LDTT Corrector
Probe: reviews/v0.1.2-schema-probe.py (run with /workspace/.venv-ldtt/bin/python from /workspace/ldtt)

## Verdict: FAIL (D3 residual, one change)
test_schema.py passes 45/45. Every v0.1.1 probe case is now rejected. F8, F9, F10 and F11 are done. Brand, scope, no-FAA wording, $0, phase order and the §9 lock (no expiry) are all clean. Handoff and evidence template are updated (tx→scope mapping noted for Phase 2).

D3 isn't fully closed. Observe is now an allowlist, but Operate blocks motion with a 7-message denylist, and MAVLink has many other ways to move a vehicle. These all validate as VALID at Operate:
- GPS_INPUT, HIL_GPS, VISION_POSITION_ESTIMATE, ODOMETRY, SET_GPS_GLOBAL_ORIGIN: feed the autopilot a false position, and it flies to "correct" it.
- FOLLOW_TARGET, LANDING_TARGET: drive the vehicle in follow and precision-land modes.
- MISSION_SET_CURRENT: jumps an AUTO mission to another waypoint, so the vehicle flies there.
- MANUAL_SETPOINT, SET_HOME_POSITION: setpoint input, and changing where RTL goes.

## DRIFT
- D3-r: Replace the Operate motion denylist with an allowlist. Operate tx = Observe read set + PARAM_SET (still gated by operate:params), MISSION_COUNT, MISSION_ITEM_INT, MISSION_CLEAR_ALL, MISSION_WRITE_PARTIAL_LIST, COMMAND_INT (carries only command_allowlist entries), and gimbal set messages (GIMBAL_MANAGER_SET_ATTITUDE, GIMBAL_MANAGER_SET_PITCHYAW). Every other message is Command-only in v0.1; the Phase 2 mapping can widen this in v0.2. Add negative tests for the messages above.
  Also add a review check under E9: at Operate, MISSION_ITEM_INT with current=2 (ArduPilot guided "go here") must be refused. The schema can't see field values.

## FIX
None.

## PLAN REF
- P3: Editing the mission or fence on an armed vehicle in AUTO can change its path. That's allowed at Operate with confirmation. For v0.2, decide whether Operate writes apply only when the vehicle is disarmed, or require the confirmation to say the flight path will change.
- P4: Command allows MAV_CMD_DO_FLIGHTTERMINATION, PREFLIGHT_REBOOT_SHUTDOWN and DO_MOTOR_TEST. Have the Phase 2 mapping table classify them; consider making them protected in v0.2.

## Not drift
Brand, scope, non-goals, FAA wording, $0, phase order, §9, stamp/revocation formats, evidence template, handoff.
