> **SUPERSEDED by [LDTT-Evidence-Checklist-v0.1.3.md](LDTT-Evidence-Checklist-v0.1.3.md).**

# LDTT Evidence Checklist (Spec v0.1.2)

**Phase 1 template.** Copy into your connector repo as `LDTT-EVIDENCE.md`, fill every row that applies to your level, and link each file. All tests run in simulation (SITL). Self-attested in v0.1, then checked by the issuer.

| Field | Value |
|---|---|
| Connector id | |
| Version | |
| Artifact digest (`sha256:`) | |
| Level requested | observe / operate / command |
| Transport | mavlink2 / mcp |
| Egress declared? | yes / no |
| Holder contact | |
| Date | |

## Evidence

Applies: O = Observe, P = Operate, C = Command.

| ID | Evidence | Applies | Link to file(s) | Done |
|---|---|:-:|---|:-:|
| E1 | `ldtt.yaml` passes `schema/ldtt.schema.json` (paste validator output) | O P C | | ☐ |
| E2 | SPDX license identifier + SBOM file (C1) | O P C | | ☐ |
| E3 | Signed artifact + provenance; verify command and output tying digest to the public source commit (C3) | O P C | | ☐ |
| E4 | Privacy statement matching the `privacy` block; network capture or code reference showing no undeclared egress, and egress off until runtime opt-in and encrypted in transit (C2) | O P C | | ☐ |
| E5 | Sample audit log from a test session showing all required event types (C5) | O P C | | ☐ |
| E6 | Revocation tests (C4): (a) revoked: Operate/Command halt writes/commands, Observe stops egress and warns; (b) list unreachable within `max_staleness_s`: keeps last list; (c) beyond `max_staleness_s`: fails closed; (d) older `list_version` rejected | O P C | | ☐ |
| E7 | Rate-limit test showing declared limits are enforced (C6) | O P C | | ☐ |
| E8 | SITL capture showing only `tx_allowlist` messages and `command_allowlist` commands are sent, within the level limits of spec §4 (MCP: only declared tools are exposed) | O P C | | ☐ |
| E9 | Confirmation flow recording/screenshots for each write/command scope (C7); refusal of protected settings and commands (§2.1), off-allowlist params, and force-arm | P C | | ☐ |
| E10 | Heartbeat-loss test in SITL: writes/commands halt on timeout, no recovery commands sent (C8) | P C | | ☐ |
| E11 | MAVLink 2 signing enabled (capture or config), or C9 entry in `known_limitations` | C | | ☐ |
| E12 | Abuse-case notes: replayed writes/commands, stale sessions, bad input; what the connector does in each | P C | | ☐ |

## Known limitations

List anything a control can't fully meet. Must match `known_limitations` in `ldtt.yaml`.

| Control | Note |
|---|---|
| | |

## Holder attestation

I attest that the evidence above is accurate for the artifact with the digest listed, and that the connector behaves as declared in `ldtt.yaml`.

Name / handle: ______________ Date: __________

*LDTT is a connector stamp only. It does not certify aircraft, operators, or flight safety, and makes no FAA or other regulatory claim.*
