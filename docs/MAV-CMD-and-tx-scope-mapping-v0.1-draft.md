# MAV_CMD + TX message → scope mapping (v0.1 draft)

**LDTT = Linked Drone Tool Trust** · **Phase 2** shared draft · Feeds Stamp Spec v0.2  
**Status:** Draft for creator → Corrector — **not final**  
**Date:** 2026-10-06
**Creator locks applied:** REQUEST_DATA_STREAM + LOG_REQUEST_* out of ref connector; P4=Command; no Operate tx widening; no schema bump.

Maps **sent (tx) MAVLink messages** and **MAV_CMD_*** values to LDTT scopes / levels. Complements schema `$defs/observeTx`, `$defs/operateTx`, and level-limited `command_allowlist` rules (spec §4). Parameter writes remain gated by `param_allowlist` + §2.1 protected denylist.

Legend: **O** = Observe allowed · **P** = Operate (needs confirmation) · **C** = Command · **X** = denied at every stamp level (protected / v0.1) · **?** = open for Corrector

---

## 1. TX messages (selected)

| Message | Min level | Scope(s) | Notes |
|---|---|---|---|
| HEARTBEAT | O | observe:telemetry | GCS heartbeat |
| REQUEST_DATA_STREAM | O (schema) | observe:telemetry | **Creator lock:** REMOVED from `ldtt-ref-mav-observer` tx_allowlist + enforcement (F8 / PX4-friendly). Prefer REQUEST_MESSAGE / SET_MESSAGE_INTERVAL. |
| PARAM_REQUEST_READ / LIST | O | observe:telemetry | Read-only |
| MISSION_REQUEST_LIST / INT, MISSION_ACK | O | observe:telemetry | Read mission state |
| LOG_REQUEST_* | O (schema, needs observe:logs) | observe:logs | **Creator lock:** omitted from ref-mav-observer tx_allowlist + enforcement (scopes=`observe:telemetry` only; least privilege). |
| COMMAND_LONG | O* | (per command) | *Only if command ∈ level allowlist |
| PARAM_SET | P | operate:params | Needs param_allowlist; no protected names |
| MISSION_COUNT, MISSION_ITEM_INT, MISSION_CLEAR_ALL, MISSION_WRITE_PARTIAL_LIST | P | operate:mission | E9: refuse guided-goto `current=2` at Operate |
| COMMAND_INT | P | (per command) | Camera/payload cmds at Operate; flight at Command |
| GIMBAL_MANAGER_SET_ATTITUDE / SET_PITCHYAW | P | operate:payload | |
| SET_POSITION_TARGET_*, SET_ATTITUDE_TARGET, RC_CHANNELS_OVERRIDE, MANUAL_CONTROL, SET_MODE, … | C | command:* | Motion / flight-state |
| GPS_INPUT, VISION_POSITION_ESTIMATE, ODOMETRY, FOLLOW_TARGET, LANDING_TARGET, MISSION_SET_CURRENT, SET_HOME_POSITION | C | command:* | Command-only in v0.1 (D3-r) |

### Proposed Operate tx allowlist widening (for v0.2 discussion)

| Candidate | Proposal | Rationale | Risk |
|---|---|---|---|
| MISSION_REQUEST_LIST already O | — | — | — |
| `FENCE_POINT` / fence upload msgs (if standardized) | Consider P under `operate:geofence` | Spec allows edit fence items | Must never disable fence |
| `CAMERA_TRACK_*` / tracking set | Consider P vs C | Payload vs motion coupling | May imply follow behavior → prefer C |
| `PLAY_TUNE` / `LED_CONTROL` | Consider P `operate:payload` | Non-motion | Low |
| `TRAJECTORY_REPRESENTATION_*` | Keep C | Motion path | High |

**No widening applied in v0.1.3 schema.** Table only proposes candidates for Corrector/creator before v0.2.

---

## 2. MAV_CMD classification (selected + Corrector P4)

### Observe read-request (allowed at O)

| Command | Level | Scope | Notes |
|---|---|---|---|
| MAV_CMD_REQUEST_MESSAGE | O | observe:telemetry | Stream setup (PX4+AP) |
| MAV_CMD_SET_MESSAGE_INTERVAL | O | observe:telemetry | Stream setup (PX4+AP) |

### Protected (X — may not appear in any command_allowlist v0.1)

| Command | Level | Notes |
|---|---|---|
| MAV_CMD_DO_FENCE_ENABLE | X | §2.1 geofence enable/disable |
| MAV_CMD_DO_SET_PARAMETER | X | Bypasses param_allowlist |
| MAV_CMD_PREFLIGHT_STORAGE | X | Param reset / storage bypass |

### Corrector P4 — classify (draft proposal)

| Command | v0.1 draft class | Scope if allowed | v0.2 protect? | Rationale |
|---|---|---|---|---|
| **MAV_CMD_DO_FLIGHTTERMINATION** | **C** | command:mode (or dedicated) | **Propose protect (X) in v0.2** | Ends flight / kills motors; irreversible safety action; should not be stampable casually |
| **MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN** | **C** | command:mode | **Propose protect (X) or gated C with strong confirmation in v0.2** | Can interrupt failsafes / Remote ID continuity mid-flight if abused |
| **MAV_CMD_DO_MOTOR_TEST** | **C** | command:arm-adjacent | **Propose protect (X) on armed vehicle; allow only disarmed lab use later** | Spins motors; ground-safety hazard |

### Other commands (abbreviated)

| Command family | Level | Scope |
|---|---|---|
| IMAGE_*/VIDEO_*/CAMERA_*/DO_GIMBAL_*/DO_MOUNT_* | P | operate:payload |
| MAV_CMD_DO_SET_ROI* | C | command:reposition |
| MAV_CMD_COMPONENT_ARM_DISARM | C | command:arm |
| MAV_CMD_NAV_TAKEOFF / LAND / RETURN_TO_LAUNCH | C | command:takeoff_land |
| MAV_CMD_DO_SET_MODE / DO_CHANGE_SPEED / DO_REPOSITION | C | command:mode / reposition |
| MAV_CMD_MISSION_START / DO_PAUSE_CONTINUE | C | command:mission_control |

---

## 3. Open questions for Corrector (via creator)

1. Confirm P4: FLIGHTTERMINATION / REBOOT_SHUTDOWN / MOTOR_TEST as Command now; protect in v0.2?
2. Any Operate tx widening accepted for v0.2 from the candidate table?
3. ~~LOG_REQUEST_* when scopes omit observe:logs?~~ **Locked:** omit from this connector. Schema may keep them for connectors that declare `observe:logs`.
4. Force-arm (`param2` on ARM_DISARM) — keep review-only (E9) or schema-detectable later?

---
*Phase 2 draft · Linked Drone Tool Trust · not final*
