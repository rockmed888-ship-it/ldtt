> **Corrector PASS (2026-10-06). Superseded by [LDTT-Stamp-Spec-v0.1.4.md](LDTT-Stamp-Spec-v0.1.4.md)**, a schema-only patch (revocation `list_url` may be https, file:, or relative). Levels, controls, and non-goals are unchanged.

# LDTT Stamp Spec v0.1.3 (Draft)

**LDTT = Linked Drone Tool Trust**
**Phase 1 deliverable** · Status: Draft for Corrector re-review · Date: 2026-10-06 · Owner: LDTT Spec Writer · Lead: creator
Supersedes v0.1.2 (Corrector FAIL on D3-r). Companion files: `schema/ldtt.schema.json`, `schema/test_schema.py`, `examples/ldtt.observe.example.yaml`, `templates/LDTT-Evidence-Checklist-v0.1.3.md`, `LDTT-Phase2-Handoff.md`.

> An LDTT stamp says one thing: *this drone software connector declares what it can touch, proves who built it, and can be cut off.* It is a connector stamp only. It does not certify aircraft, operators, airworthiness, or flight safety, and makes no FAA or other regulatory claim.

### Changes in v0.1.3 (from v0.1.2)
| ID | Change | Where |
|---|---|---|
| D3-r | Operate `tx_allowlist` is now an allowlist, like Observe: the Observe read-only set plus mission upload, gated `PARAM_SET`, `COMMAND_INT`, and gimbal set messages. Every other message is Command-only in v0.1. New E9 check: guided-goto mission items refused at Operate. | §2, §4, §7, schema |
| P3, P4 | Corrector plan items logged for later (mission edits on an armed vehicle; flight termination, reboot, motor test). | §10 |

### Changes in v0.1.2 (from v0.1.1)
| ID | Change | Where |
|---|---|---|
| D3 | `tx_allowlist` is limited by level: Observe sends read-only messages only; motion messages are denied below Command; `PARAM_SET` needs `operate:params` + `param_allowlist`. `MAV_CMD_DO_SET_PARAMETER` and `MAV_CMD_PREFLIGHT_STORAGE` are protected. ROI commands moved to Command. | §2, §2.1, §4, schema |
| F8 | Observe may send the read-request commands `MAV_CMD_REQUEST_MESSAGE` and `MAV_CMD_SET_MESSAGE_INTERVAL`. | §2, §4, schema |
| F9 | ArduPilot `DID_*` (Remote ID) added to the protected-settings denylist. | §2.1, schema |
| F10 | MCP tool scopes limited by connector level, like top-level scopes. | §4, schema |
| F11 | `level` must equal the highest declared scope. | §2, §4, schema |

### Changes in v0.1.1 (from v0.1)
| ID | Change | Where |
|---|---|---|
| D1 | `operate:params` needs a declared param allowlist; protected safety settings can't be stamped at any level; geofence may be edited, never disabled. | §2.1, §4 |
| D2 | Revocation behavior defined: revoked, unreachable list, staleness, Observe behavior. | C4, §5.2 |
| F1 | `message_allowlist` split into `rx_allowlist` and `tx_allowlist`. | §4 |
| F2 | At Operate, `command_allowlist` holds only non-motion camera/payload commands. | §2, §4 |
| F3 | Observe example has no write or command rate limits. | §4 |
| F4 | Stamp record fields and signed revocation list format defined. | §5 |
| F5 | Non-goal 5 reworded; no program named. | §6 |
| F6 | `pii: false` replaced by a personal-data categories list. | §4 |
| F7 | Replay and stale-session notes (E12) extended to Operate. | §7 |
| §9 | Creator decisions applied: cosign-signed files, egress needs runtime opt-in and a stamp flag, MCP `tools` block, no time expiry. | §4, §5, §9 |

---

## 1. Scope and terms

- **Connector**: software that links a tool (ground station, AI agent, dashboard, script) to a drone or its data, over MAVLink 2 or an MCP-style tool server in v0.1. Vendor-API-only connectors are deferred to a later phase.
- **Stamp**: a signed record (§5.1) that one connector *version* met the controls for one level.
- **Holder**: the publisher of the connector.
- **Operator**: the human responsible for the drone the connector is used with.
- **Issuer**: the party that signs stamps and the revocation list. In v0.1 this is LDTT, via cosign-signed files in LDTT's public git repo. The full issuer and reviewer model is deferred (§10).
- MAVLink-first: where a vehicle link is involved, MAVLink 2 is the reference transport.

A stamp binds to `connector_id + version + build digest`. Any new build needs a new stamp. There is no time-based expiry in v0.1.

## 2. Stamp levels

Levels are cumulative: each includes all controls of the level below.

| Level | What the connector may do | What it may not do |
|---|---|---|
| **Observe** | Receive telemetry, status, logs, mission state, parameters, media metadata. Send only read requests: the read-only message set (§4) and the read-request commands `MAV_CMD_REQUEST_MESSAGE` and `MAV_CMD_SET_MESSAGE_INTERVAL`. | Write to the vehicle, payload, mission, or parameters. Send any other command. |
| **Operate** | Observe, plus non-motion changes: upload/edit mission plans, edit geofences, set parameters on its declared allowlist, and send non-motion camera/payload commands. Every write needs operator confirmation before it takes effect. | Change vehicle motion, heading, or flight state, by command or by message. Operate may send only the messages on its allowlist (§4); everything else, including position or sensor injection (e.g. `GPS_INPUT`, `VISION_POSITION_ESTIMATE`), follow/landing targets, mission jumps, and home changes, is Command-only. Point the vehicle at a location (ROI). Touch protected safety settings (§2.1). |
| **Command** | Operate, plus flight-state commands: arm/disarm, takeoff, land, mode change, reposition/goto (including ROI, under `command:reposition`), RTL, mission start/pause, and motion messages. | Bypass operator confirmation, the operator's own stop/override, or the vehicle's onboard failsafes. Touch protected safety settings (§2.1). |

Scopes are declared at a finer grain inside each level (§4 `scopes`). `level` must equal the highest level among its declared scopes. The mapping of every MAV_CMD and every sent message to a scope is a Phase 2 deliverable (§10).

### 2.1 Protected safety settings (no stamp at any level in v0.1)

A connector that can change any of the following cannot be stamped at any level in v0.1:
1. Geofence enable/disable or fence breach action (e.g. ArduPilot `FENCE_ENABLE`, `FENCE_ACTION`; PX4 `GF_ACTION`), including disabling the fence by command (`MAV_CMD_DO_FENCE_ENABLE` may not appear in any `command_allowlist` in v0.1). `operate:geofence` may add, move, or edit fence items, but never disable the fence.
2. Failsafe settings (e.g. ArduPilot `FS_*`, `BATT_FS_*`; PX4 `NAV_DLL_ACT`, `NAV_RCL_ACT`).
3. Arming checks (e.g. ArduPilot `ARMING_CHECK`; PX4 `COM_ARM_*`), including force-arm commands that skip them.
4. Any setting or command that disables or degrades Remote ID (e.g. ArduPilot `DID_*`; PX4 `COM_ARM_ODID`).
5. Generic parameter writes or resets that bypass `param_allowlist`: `MAV_CMD_DO_SET_PARAMETER` and `MAV_CMD_PREFLIGHT_STORAGE` may not appear in any `command_allowlist` in v0.1.

Parameter names above are examples. The full per-autopilot list comes with the Phase 2 mapping table. `operate:params` requires an explicit `param_allowlist` in the manifest; anything not listed may not be written, and the allowlist may not contain protected settings or wildcards that match them.

## 3. Mandatory controls

✔ = required at that level.

| # | Control | Observe | Operate | Command | Requirement |
|---|---|:-:|:-:|:-:|---|
| C1 | **License attestation** | ✔ | ✔ | ✔ | License declared as an SPDX identifier; dependency licenses listed in an SBOM; no license conflict with declared use. |
| C2 | **Privacy rails** | ✔ | ✔ | ✔ | Declares every data category collected, every personal-data category, every egress destination, and retention. Egress (data leaving the operator's own systems) is allowed only if fully declared **and** the operator opts in at runtime; it is off until they do, and encrypted in transit. Undeclared egress means the stamp is denied, or revoked if found later. The stamp record shows an egress flag. |
| C3 | **Signed builds** | ✔ | ✔ | ✔ | Every release artifact is signed and has build provenance linking it to a public source commit. Free tooling is enough (e.g. Sigstore cosign, SLSA-style provenance from CI). |
| C4 | **Revoke** | ✔ | ✔ | ✔ | Connector checks the signed revocation list (§5.2) at startup and every `check_interval_s`. **If revoked:** Operate/Command stop all writes and commands; Observe stops all egress and warns the operator. **If the list is unreachable:** keep using the last valid signed list until it is older than `max_staleness_s` (measured from the list's `issued_at`), then fail closed (same behavior as revoked). The operator can also revoke the connector's access locally at any time. |
| C5 | **Audit log** | ✔ | ✔ | ✔ | Append-only local log in a documented, exportable format. All levels: sessions, scopes granted, egress opt-in changes, revocation checks and outcomes. Operate/Command add every write or command with timestamp, operator confirmation, and result. |
| C6 | **Rate limits** | ✔ | ✔ | ✔ | Declared max rates, enforced in the connector, not just documented. Must not flood the vehicle link. Observe declares read limits only. |
| C7 | **Operator confirmation** |  | ✔ | ✔ | Each write or command is confirmed by a human before execution. No batch or standing approvals in v0.1 (batch policy deferred to v0.2). |
| C8 | **Heartbeat + fail-safe on loss** |  | ✔ | ✔ | On heartbeat timeout the connector stops sending writes and commands and leaves the vehicle under its own failsafe behavior. It never sends commands to "recover" a lost link. |
| C9 | **Link authentication** |  |  | ✔ | Vehicle link authenticated where the transport supports it (MAVLink 2 message signing preferred). If unavailable, stated as a known limitation on the stamp. |

## 4. Connector contract (manifest)

Every stamped connector ships an `ldtt.yaml` manifest, validated by `schema/ldtt.schema.json`. Example below is an **Observe** connector (also in `examples/ldtt.observe.example.yaml`). Fields used only at higher levels are shown commented.

```yaml
ldtt_spec: "0.1.3"
connector:
  id: "org.example.mav-observer"          # reverse-DNS, stable across versions
  name: "Example MAVLink Observer"
  version: "1.2.0"                        # semver
  publisher: "Example Org"
  security_contact: "security@example.org"
  source_url: "https://example.org/src/mav-observer"
  license: "Apache-2.0"                   # SPDX (C1)
  sbom: "sbom.spdx.json"                  # (C1)

build:                                    # (C3)
  artifact_digest: "sha256:0000000000000000000000000000000000000000000000000000000000000000"
  signature: "dist/mav-observer.sigstore.json"   # cosign bundle
  provenance: "dist/provenance.intoto.jsonl"
  source_commit: "0000000000000000000000000000000000000000"

transport:
  kind: "mavlink2"                        # mavlink2 | mcp
  mavlink:
    signing: false                        # must be true at Command, or listed in known_limitations (C9)
    rx_allowlist: [HEARTBEAT, SYS_STATUS, GLOBAL_POSITION_INT, ATTITUDE, BATTERY_STATUS]
    tx_allowlist: [HEARTBEAT, REQUEST_DATA_STREAM, PARAM_REQUEST_LIST, COMMAND_LONG]   # level-limited; Observe: read-only set
    command_allowlist: [MAV_CMD_REQUEST_MESSAGE, MAV_CMD_SET_MESSAGE_INTERVAL]   # Observe: these two read requests only
    # param_allowlist: []                 # required with operate:params; no protected settings (§2.1)
  # mcp:                                  # when kind: mcp
  #   tools:
  #     - name: "get_telemetry"
  #       scope: "observe:telemetry"
  #       writes: false

auth:
  method: "local-only"                    # local-only | token | oauth2 | mtls
  token_storage: "none"                   # never plaintext in config
  session_ttl_s: 3600

level: "observe"                          # observe | operate | command
scopes:                                   # least privilege
  - "observe:telemetry"
  - "observe:logs"
  # operate:mission, operate:geofence, operate:params, operate:payload
  # command:arm, command:takeoff_land, command:mode, command:reposition, command:mission_control

# heartbeat:                              # required at Operate/Command (C8)
#   interval_s: 1
#   timeout_s: 5
#   on_timeout: "halt_writes"             # only allowed value in v0.1

rate_limits:                              # (C6) Observe: reads only
  reads_per_s: 20
  # writes_per_min / commands_per_min: omit or 0 at Observe

privacy:                                  # (C2)
  collects: ["vehicle_location", "telemetry"]
  personal_data: []                       # categories, e.g. operator_identity, precise_location,
                                          # imagery_of_people, device_identifiers; [] = none
  egress: []                              # each entry: destination, data, purpose
  egress_runtime_opt_in: true             # required true whenever egress is non-empty
  retention_days: 0                       # 0 = not stored beyond session

audit_log:                                # (C5)
  format: "jsonl"
  path: "~/.ldtt/audit/org.example.mav-observer.jsonl"
  includes: ["session", "scope_grant", "egress_opt_in", "revocation_check"]

revocation:                               # (C4)
  list_url: "https://example.org/ldtt/revocations/revocations.json"   # LDTT public repo file
  check_interval_s: 3600
  max_staleness_s: 86400

# operator_confirmation:                  # required at Operate/Command (C7)
#   required_for: ["operate:*", "command:*"]
#   ui: "how confirmation is shown"

known_limitations: []                     # each entry: {control: "C1".."C9", note: "..."}, stated plainly
```

Level rules the schema enforces:
- **All levels:** `level` equals the highest declared scope (Observe: only `observe:*`; Operate: at least one `operate:*`, no `command:*`; Command: at least one `command:*`). `tx_allowlist` is level-limited as below. `PARAM_SET` in `tx_allowlist` requires `operate:params` and a `param_allowlist`. Protected commands (§2.1) are denied everywhere.
- **Observe:** `tx_allowlist` only from the read-only set: `HEARTBEAT`, `REQUEST_DATA_STREAM`, `PARAM_REQUEST_READ`, `PARAM_REQUEST_LIST`, `MISSION_REQUEST_LIST`, `MISSION_REQUEST_INT`, `MISSION_ACK`, `LOG_REQUEST_LIST`, `LOG_REQUEST_DATA`, `LOG_REQUEST_END`, `COMMAND_LONG`. `command_allowlist` only `MAV_CMD_REQUEST_MESSAGE` and `MAV_CMD_SET_MESSAGE_INTERVAL`. No `param_allowlist`; write/command rate limits omitted or 0.
- **Operate:** `heartbeat` and `operator_confirmation` required; `param_allowlist` required if `operate:params` is declared; `tx_allowlist` only from the Observe read-only set plus `PARAM_SET` (gated as above), `MISSION_COUNT`, `MISSION_ITEM_INT`, `MISSION_CLEAR_ALL`, `MISSION_WRITE_PARTIAL_LIST`, `COMMAND_INT` (carries only `command_allowlist` entries), `GIMBAL_MANAGER_SET_ATTITUDE`, `GIMBAL_MANAGER_SET_PITCHYAW`. Every other message is Command-only in v0.1. `command_allowlist` holds only camera/payload MAV_CMDs (e.g. `MAV_CMD_IMAGE_START_CAPTURE`, `MAV_CMD_VIDEO_START_CAPTURE`, gimbal commands) plus the two read requests. ROI commands are not camera/payload. Field values (e.g. a guided-goto mission item) can't be checked by the schema and are covered by E9.
- **Command:** Operate rules plus `mavlink.signing: true` or a C9 entry in `known_limitations`; any message not otherwise denied, plus flight-state commands, allowed.
- **MCP:** `transport.mcp.tools` required; every tool names one scope and whether it writes. Tool scopes are limited by level exactly like top-level scopes. That each tool scope also appears in `scopes` is a review check. If the MCP front end drives a MAVLink vehicle link, the `mavlink` block is required too and all MAVLink rules apply.

## 5. Stamp record and revocation list

Both live as JSON files in LDTT's public git repo, each signed with `cosign sign-blob` and published with its Sigstore bundle next to it.

```
stamps/<connector_id>/<version>.json
stamps/<connector_id>/<version>.json.sigstore.json
revocations/revocations.json
revocations/revocations.json.sigstore.json
```

### 5.1 Stamp record

```json
{
  "ldtt_spec": "0.1.3",
  "connector_id": "org.example.mav-observer",
  "version": "1.2.0",
  "digest": "sha256:…",
  "level": "observe",
  "scopes": ["observe:telemetry", "observe:logs"],
  "transport": "mavlink2",
  "egress": false,
  "known_limitations": [],
  "issuer": "LDTT",
  "issued_at": "2026-10-06T00:00:00Z",
  "signature": "org.example.mav-observer/1.2.0.json.sigstore.json"
}
```

`expires_at` is a reserved optional field. Issuers **must omit it** in v0.1 (no time-based expiry, §9). Consumers verify the signature bundle, then check `digest` against the artifact they're running.

### 5.2 Revocation list

```json
{
  "ldtt_spec": "0.1.3",
  "issuer": "LDTT",
  "list_version": 7,
  "issued_at": "2026-10-06T00:00:00Z",
  "revoked": [
    {
      "connector_id": "org.example.bad-connector",
      "version": "2.0.1",
      "digest": "sha256:…",
      "revoked_at": "2026-10-05T18:00:00Z",
      "reason": "undeclared egress"
    }
  ]
}
```

- `version: "*"` revokes every version of that connector.
- `list_version` only increases. A connector rejects any list with a lower `list_version` than the last one it accepted (no rollback).
- Staleness for C4 is measured from `issued_at`. The issuer re-signs and republishes the list at least as often as the shortest `max_staleness_s` it accepts in stamped manifests.

## 6. Explicit non-goals

LDTT does **not**:
1. Certify aircraft, airworthiness, or flight safety, or make any FAA or other regulatory claim.
2. Certify operators, pilots, or missions.
3. Provide a fleet dashboard, ground control station, or flight software.
4. Replace or override autopilot failsafes, geofencing, or Remote ID.
5. Serve as a rebrand or successor of any prior program.
6. Guarantee a connector is bug-free. A stamp attests to declared behavior and evidence, not correctness.
7. Require paid tooling, paid audits, or vendor lock-in to earn a stamp (v0.1).

## 7. Evidence required to earn a stamp

Submitted as files in the connector's public repo or attached to the release. Self-attested in v0.1, then checked by the issuer. Template: `templates/LDTT-Evidence-Checklist-v0.1.3.md`.

| Evidence | Observe | Operate | Command |
|---|:-:|:-:|:-:|
| E1. `ldtt.yaml` passes `schema/ldtt.schema.json` | ✔ | ✔ | ✔ |
| E2. SPDX license + SBOM (C1) | ✔ | ✔ | ✔ |
| E3. Signed artifact + provenance verifiable against public source commit (C3) | ✔ | ✔ | ✔ |
| E4. Privacy statement matching the `privacy` block; network capture or code reference showing no undeclared egress, and egress off until runtime opt-in and encrypted in transit (C2) | ✔ | ✔ | ✔ |
| E5. Sample audit log from a test session (C5) | ✔ | ✔ | ✔ |
| E6. Revocation tests: revoked behavior, unreachable list within and beyond `max_staleness_s`, rollback rejected (C4) | ✔ | ✔ | ✔ |
| E7. Rate-limit test showing enforcement (C6) | ✔ | ✔ | ✔ |
| E8. SITL test (e.g. ArduPilot or PX4 SITL) showing only `tx_allowlist` messages and `command_allowlist` commands are sent, and that the lists respect the level limits in §4 | ✔ | ✔ | ✔ |
| E9. Confirmation flow recording or screenshots for each write/command scope (C7); attempts to write protected settings or commands (§2.1) or off-allowlist params are refused; at Operate, a `MISSION_ITEM_INT` with `current=2` (ArduPilot guided "go here") is refused |  | ✔ | ✔ |
| E10. Heartbeat-loss test in SITL: writes/commands halt on timeout (C8) |  | ✔ | ✔ |
| E11. Link authentication evidence (MAVLink 2 signing enabled) or stated limitation (C9) |  |  | ✔ |
| E12. Abuse-case notes: replayed writes/commands, stale sessions, and bad input |  | ✔ | ✔ |

All tests run in simulation. No live-flight evidence is required or accepted as a substitute in v0.1.

## 8. Phase 1 exit criteria

| # | Criterion | Status |
|---|---|---|
| 1 | Spec passes LDTT Corrector review with no open drift flags | **Open**: v0.1 FAIL, v0.1.1 FAIL (D3), v0.1.2 FAIL (D3-r); v0.1.3 awaiting re-review |
| 2 | Levels, controls C1–C9, and non-goals frozen for v0.1.x; changes go to v0.2 | Open (freezes on Corrector PASS) |
| 3 | JSON Schema for `ldtt.yaml` drafted and validates the §4 example | Drafted: `schema/ldtt.schema.json`; validates the §4 example, and all level-rule cases (including each D3/F8–F11 case) pass in `schema/test_schema.py` |
| 4 | Evidence checklist E1–E12 as a standalone template | Drafted: `templates/LDTT-Evidence-Checklist-v0.1.3.md` |
| 5 | Open questions resolved or assigned to a later phase | Done (§9, §10) |
| 6 | Total spend $0; every required tool free/open | Met |
| 7 | Phase 2 handoff note naming one Observe reference connector | Drafted: `LDTT-Phase2-Handoff.md` |

## 9. Decisions (creator, locked for v0.1.x)

1. **Stamps and revocation: DECIDED.** Cosign-signed files in LDTT's public git repo; records carry `issued_at` for staleness.
2. **Observe with egress: DECIDED.** Allowed only if fully declared and the operator opts in at runtime. Undeclared egress means deny, or revoke if found later. The stamp shows an egress flag. No new level.
3. **MCP transport: DECIDED.** In scope as a transport kind with a required `tools` block. First reference connector is MAVLink Observe. Vendor-API-only connectors come later.
4. **Time expiry: DECIDED.** None in v0.1. Binding is `connector_id + version + digest`; revocation handles bad actors. `expires_at` is reserved and must be omitted.

## 10. Deferred

- Mapping table of MAV_CMDs **and sent (tx) MAVLink messages** to scopes, and the full per-autopilot protected-settings list: Phase 2.
- Batch or standing confirmation policy: v0.2.
- P3: mission or fence edits on an armed vehicle in AUTO can change its path. Decide for v0.2 whether Operate writes apply only when disarmed, or the confirmation must say the flight path will change.
- P4: classify `MAV_CMD_DO_FLIGHTTERMINATION`, `MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN`, and `MAV_CMD_DO_MOTOR_TEST` (Command in v0.1) in the Phase 2 mapping table; consider protecting them in v0.2.
- Widening the Operate tx allowlist: via the Phase 2 mapping table, in v0.2.
- Issuer and reviewer model (who checks evidence, how reviewers are named): later phase.
- Vendor-API-only connectors: later phase.

---
*LDTT Stamp Spec v0.1.3 · Phase 1 · Draft. Connector stamp only; not aircraft certification; not a fleet dashboard; not a rebrand or successor of any prior program; no FAA claims.*
