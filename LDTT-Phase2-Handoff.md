# LDTT Phase 1 → Phase 2 Handoff Note

**From:** LDTT Spec Writer (Phase 1) · **To:** LDTT Open Builder (Phase 2) · **Lead:** creator · **Date:** 2026-10-06
**Basis:** LDTT Stamp Spec v0.1.4 (v0.1.3 PASS + schema-only patch allowing an offline revocation list_url).

## Reference connector to build

**`ldtt-ref-mav-observer`**: a read-only MAVLink 2 telemetry observer, stamped at **Observe** level.

- Transport: `mavlink2`. Receives `HEARTBEAT`, `SYS_STATUS`, `GLOBAL_POSITION_INT`, `ATTITUDE`, `BATTERY_STATUS`; sends only messages from the Observe read-only set (spec §4). `command_allowlist` holds only `MAV_CMD_REQUEST_MESSAGE` and `MAV_CMD_SET_MESSAGE_INTERVAL`; use these for stream setup so it works on PX4 as well as ArduPilot (PX4 largely ignores `REQUEST_DATA_STREAM`). No `param_allowlist`.
- Scopes: `observe:telemetry` only.
- Privacy: no egress, no personal data, nothing stored beyond the session. Shows data locally (CLI or simple local page).
- Start from `examples/ldtt.observe.example.yaml` and change ids and URLs.
- Suggested free stack (Builder's call): Python with pymavlink (LGPL-3.0) or MAVSDK-Python (BSD-3-Clause); ArduPilot SITL for tests; a public git repo with free CI for builds, cosign keyless signing, and provenance.

## Definition of done

1. `ldtt.yaml` passes `schema/ldtt.schema.json`.
2. Revocation check (C4) implemented against a signed `revocations.json` with `max_staleness_s`, including rollback rejection.
3. Audit log (C5) and enforced rate limits (C6).
4. Evidence E1–E8 filled in `templates/LDTT-Evidence-Checklist-v0.1.3.md`.
5. First stamp record (§5.1) and empty revocation list (§5.2) published as cosign-signed files in LDTT's public repo.
6. $0 spend.

## Also owed in Phase 2 (deferred from Phase 1)

- Mapping table to scopes covering **both MAV_CMDs and sent (tx) MAVLink messages** (Corrector P1). It feeds the level-limited `tx_allowlist` and `command_allowlist` rules in the schema and goes into v0.2. It should also classify `MAV_CMD_DO_FLIGHTTERMINATION`, `MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN`, and `MAV_CMD_DO_MOTOR_TEST` (Corrector P4) and propose any widening of the Operate tx allowlist.
- Full per-autopilot protected-settings list (ArduPilot and PX4) for §2.1 and the schema denylist.

## Not in Phase 2 scope

Operate/Command connectors, MCP reference connector, vendor-API connectors, batch confirmation (v0.2), issuer/reviewer model.
