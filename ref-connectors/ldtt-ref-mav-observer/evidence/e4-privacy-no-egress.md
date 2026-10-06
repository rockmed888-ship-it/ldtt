# E4 — Privacy / no undeclared egress (Phase 2 draft)

**Date:** 2026-10-06 CT · **Not final**

## Declaration (`ldtt.yaml`)

- `privacy.collects`: vehicle_location, telemetry
- `privacy.personal_data`: []
- `privacy.egress`: []
- `privacy.retention_days`: 0
- Stamp/record `egress: false` on placeholder stamp

## Code references

- `src/ldtt_ref_mav_observer/cli.py` — stdout display only
- No telemetry upload / cloud SDK imports under `src/`
- Default revocation `list_url` is a **relative local path** (v0.1.4); no network required for C4 when using placeholders
- `audit_log` writes local JSONL control events only

## Wire evidence

- `evidence/e8-real-sitl-wire-capture.json` — connector-side TX decode on real SITL link
- TX set = {HEARTBEAT, COMMAND_LONG(511/512)} only

## Gaps (honest)

- No host-wide packet capture or egress firewall deny-test
- If operator sets HTTPS `list_url`, revocation fetch is declared LDTT list fetch (not vehicle telemetry egress)
