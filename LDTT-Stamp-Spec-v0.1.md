> **SUPERSEDED by [LDTT-Stamp-Spec-v0.1.1.md](LDTT-Stamp-Spec-v0.1.1.md)** after Corrector FAIL (2026-10-06). Kept for history only; do not use.

# LDTT Stamp Spec v0.1 (Draft)

**LDTT = Linked Drone Tool Trust**
**Phase 1 deliverable** · Status: Draft for Corrector review · Date: 2026-10-06 · Owner: LDTT Spec Writer · Lead: creator

> An LDTT stamp says one thing: *this drone software connector declares what it can touch, proves who built it, and can be cut off.* It is a connector stamp only. It does not certify aircraft, operators, airworthiness, or flight safety, and makes no FAA or other regulatory claim.

---

## 1. Scope and terms

- **Connector**: software that links a tool (ground station, AI agent, dashboard, script) to a drone or its data, e.g. over MAVLink, an MCP-style tool server, or a vendor API.
- **Stamp**: a signed record that a specific connector *version* met the controls for one level.
- **Holder**: the publisher of the connector.
- **Operator**: the human responsible for the drone the connector is used with.
- MAVLink-first: where a vehicle link is involved, MAVLink 2 is the reference transport. Other transports may be stamped if they meet the same controls.

A stamp binds to `connector_id + version + build digest`. Any new build needs a new stamp.

## 2. Stamp levels

Levels are cumulative: each includes all controls of the level below.

| Level | What the connector may do | What it may not do |
|---|---|---|
| **Observe** | Read telemetry, status, logs, mission state, parameters, media metadata. | Write anything to the vehicle, payload, or mission. |
| **Operate** | Observe, plus change non-motion state: upload/edit mission plans, geofences, parameters, payload/camera settings. Every write needs explicit operator confirmation before it takes effect on the vehicle. | Issue commands that change vehicle motion or flight state. |
| **Command** | Operate, plus flight-state commands: arm/disarm, takeoff, land, mode change, reposition/goto, RTL, mission start/pause. | Bypass operator confirmation, the operator's own stop/override, or the vehicle's onboard failsafes. |

Scopes are declared at a finer grain inside each level (see §4, `scopes`). A connector is stamped at the highest level among its declared scopes.

## 3. Mandatory controls

✔ = required at that level.

| # | Control | Observe | Operate | Command | Requirement |
|---|---|:-:|:-:|:-:|---|
| C1 | **License attestation** | ✔ | ✔ | ✔ | Connector license declared as an SPDX identifier; dependency licenses listed (SBOM); no license conflict with declared use. |
| C2 | **Privacy rails** | ✔ | ✔ | ✔ | Declares every data category it collects (location, imagery, operator identity, etc.), where it sends it (egress list), and retention. Default: no egress beyond the operator's own systems. No silent telemetry or phone-home. |
| C3 | **Signed builds** | ✔ | ✔ | ✔ | Every release artifact is signed and has build provenance linking it to a public source commit. Free tooling is sufficient (e.g. Sigstore/cosign, SLSA-style provenance from CI). |
| C4 | **Revoke** | ✔ | ✔ | ✔ | Stamp can be revoked; the connector checks revocation status at startup and on a declared interval, and fails closed for Operate/Command if revoked. Operator can revoke the connector's access locally at any time. |
| C5 | **Audit log** | ✔ | ✔ | ✔ | Append-only local log of sessions, scopes granted, and (Operate/Command) every write or command with timestamp, operator confirmation, and result. Exportable in a documented format. Observe: session-level only. |
| C6 | **Rate limits** | ✔ | ✔ | ✔ | Declared max request/command rates; enforced in the connector, not just documented. Must not flood the vehicle link. |
| C7 | **Operator confirmation** |  | ✔ | ✔ | Each write/command is confirmed by a human before execution. Command level: no batch or standing approvals for flight-state commands in v0.1. |
| C8 | **Heartbeat + fail-safe on loss** |  | ✔ | ✔ | Connector emits/consumes a heartbeat; on timeout it stops sending writes/commands and leaves the vehicle under its own failsafe behavior. It never issues commands to "recover" a lost link. |
| C9 | **Link authentication** |  |  | ✔ | Vehicle link authenticated where the transport supports it (MAVLink 2 message signing preferred). If unavailable, stated as a known limitation on the stamp. |

## 4. Connector contract (manifest)

Every stamped connector ships an `ldtt.yaml` manifest. Fields marked **R** are required.

```yaml
ldtt_spec: "0.1"                         # R
connector:
  id: "org.example.mav-observer"         # R, reverse-DNS, stable across versions
  name: "Example MAVLink Observer"       # R
  version: "1.2.0"                       # R, semver
  publisher: "Example Org"               # R
  security_contact: "security@example.org"  # R
  source_url: "https://..."              # R, public source
  license: "Apache-2.0"                  # R, SPDX (C1)
  sbom: "sbom.spdx.json"                 # R (C1)

build:                                   # R (C3)
  artifact_digest: "sha256:..."
  signature: "cosign bundle path or URL"
  provenance: "provenance.intoto.jsonl"
  source_commit: "git sha"

transport:                               # R
  kind: "mavlink2"                       # mavlink2 | mcp | http | stdio | other
  mavlink:
    signing: true                        # R for Command (C9)
    message_allowlist: [HEARTBEAT, SYS_STATUS, GLOBAL_POSITION_INT, ATTITUDE]
    command_allowlist: []                # MAV_CMD_* allowed; must be empty at Observe

auth:                                    # R
  method: "local-only"                   # local-only | token | oauth2 | mtls
  token_storage: "OS keychain"           # never plaintext in config
  session_ttl_s: 3600

level: "observe"                         # R: observe | operate | command
scopes:                                  # R, least privilege
  - "observe:telemetry"
  - "observe:logs"
  # operate:mission, operate:geofence, operate:params, operate:payload
  # command:arm, command:takeoff_land, command:mode, command:reposition, command:mission_control

heartbeat:                               # R for Operate/Command (C8)
  interval_s: 1
  timeout_s: 5
  on_timeout: "halt_writes"              # only allowed value in v0.1

rate_limits:                             # R (C6)
  reads_per_s: 20
  writes_per_min: 10
  commands_per_min: 6

privacy:                                 # R (C2)
  collects: ["vehicle_location", "telemetry"]
  egress: []                             # destinations outside operator systems; empty = none
  retention_days: 0                      # 0 = not stored beyond session
  pii: false

audit_log:                               # R (C5)
  format: "jsonl"
  path: "~/.ldtt/audit/<connector_id>.jsonl"
  includes: ["session", "scope_grant", "write", "command", "confirmation", "result"]

revocation:                              # R (C4)
  check_url: "https://.../revocations.json"   # or signed file in repo
  check_interval_s: 3600
  fail_mode: "closed"                    # closed required for Operate/Command

operator_confirmation:                   # R for Operate/Command (C7)
  required_for: ["operate:*", "command:*"]
  ui: "description of how confirmation is shown"

known_limitations: []                    # anything a control can't fully meet, stated plainly
```

## 5. Explicit non-goals

LDTT does **not**:
1. Certify aircraft, airworthiness, or flight safety, or make any FAA or other regulatory claim.
2. Certify operators, pilots, or missions.
3. Provide a fleet dashboard, ground control station, or flight software.
4. Replace or override autopilot failsafes, geofencing, or Remote ID.
5. Act as HALO or any other named program.
6. Guarantee a connector is bug-free. A stamp attests to declared behavior and evidence, not correctness.
7. Require paid tooling, paid audits, or vendor lock-in to earn a stamp (v0.1).

## 6. Evidence required to earn a stamp

Submitted as files in the connector's public repo (or attached to a release). Self-attested in v0.1, then reviewed by LDTT reviewers.

| Evidence | Observe | Operate | Command |
|---|:-:|:-:|:-:|
| E1. Valid `ldtt.yaml` passing schema validation | ✔ | ✔ | ✔ |
| E2. SPDX license + SBOM (C1) | ✔ | ✔ | ✔ |
| E3. Signed artifact + provenance verifiable against public source commit (C3) | ✔ | ✔ | ✔ |
| E4. Privacy statement matching `privacy` block; network capture or code reference showing no undeclared egress (C2) | ✔ | ✔ | ✔ |
| E5. Sample audit log from a test session (C5) | ✔ | ✔ | ✔ |
| E6. Revocation test: connector shown refusing to run (or dropping to read-only) when revoked (C4) | ✔ | ✔ | ✔ |
| E7. Rate-limit test showing enforcement (C6) | ✔ | ✔ | ✔ |
| E8. Test against SITL (simulator, e.g. ArduPilot or PX4 SITL) showing only allowlisted messages/commands are sent | ✔ | ✔ | ✔ |
| E9. Confirmation flow recording or screenshots for each write/command scope (C7) |  | ✔ | ✔ |
| E10. Heartbeat-loss test in SITL: writes/commands halt on timeout (C8) |  | ✔ | ✔ |
| E11. Link authentication evidence (MAVLink 2 signing enabled) or stated limitation (C9) |  |  | ✔ |
| E12. Abuse-case notes: what happens on bad input, replayed commands, and stale sessions |  |  | ✔ |

All tests run in simulation. No live-flight evidence is required or accepted as a substitute in v0.1.

## 7. Phase 1 exit criteria

Phase 1 is done when all of these are true:
1. This spec passes LDTT Corrector review with no open drift flags (brand, scope, non-goals, no FAA claims).
2. Levels, controls C1–C9, and non-goals are frozen for v0.1; changes go to v0.2.
3. A JSON Schema for `ldtt.yaml` is drafted and validates the example in §4.
4. An evidence checklist (E1–E12) exists as a standalone template holders can copy.
5. Open questions below are each either resolved or assigned to a later phase.
6. Total spend is $0; every required tool in the spec is free/open.
7. Handoff note written for Phase 2 (Open Builder) naming one reference connector to build at Observe level.

## 8. Decisions (resolved by creator, locked for v0.1)

1. **Stamp issuance and revocation list: DECIDED.** Stamps and the revocation list are signed files in a public git repo owned by LDTT. This is the zero-budget default; `revocation.check_url` points to that repo's file.
2. **Observe with egress: DECIDED.** Allowed only if every destination is fully declared in the `privacy` block. Any undeclared egress means the stamp is denied (or revoked if found later).
3. **MCP transport: DECIDED.** In scope for v0.1 as a `transport.kind`. The first reference connector stays MAVLink at Observe level.
4. **Time expiry: DECIDED.** No time-based expiry in v0.1. A stamp binds to `connector_id + version + build digest`; revocation handles bad actors.

**Freeze status:** §8 is closed (exit criterion 5 met). v0.1 is not frozen yet. Phase 1 still needs:
- LDTT Corrector PASS (criterion 1)
- JSON Schema for `ldtt.yaml` (criterion 3)
- Evidence checklist template, E1 to E12 (criterion 4)
- Phase 2 handoff note to Open Builder (criterion 7)

---
*LDTT Stamp Spec v0.1 · Phase 1 · Draft. Connector stamp only; not aircraft certification; not a fleet dashboard; not HALO; no FAA claims.*
