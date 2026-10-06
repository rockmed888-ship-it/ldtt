# ldtt-ref-mav-observer (Phase 2 Draft)

**LDTT = Linked Drone Tool Trust** (not “Lineage”)  
**Phase 2** Observe reference connector · Lead: creator · Corrector reviews via creator — **not final**

Read-only **MAVLink 2** telemetry observer. Local CLI display only. No egress. No hardware. Real ArduCopter SITL smoke (E8); fake-peer smoke is interim only. **$0** spend.

Public repo: https://github.com/rockmed888-ship-it/ldtt

## Purpose

- Receives: `HEARTBEAT`, `SYS_STATUS`, `GLOBAL_POSITION_INT`, `ATTITUDE`, `BATTERY_STATUS`
- Sends only Observe TX: `HEARTBEAT`, `PARAM_REQUEST_LIST`, `COMMAND_LONG`
- Commands: `MAV_CMD_REQUEST_MESSAGE`, `MAV_CMD_SET_MESSAGE_INTERVAL` only
- **Locked out:** `REQUEST_DATA_STREAM`, `LOG_REQUEST_*` (creator Phase 2 locks)
- Scope: `observe:telemetry` only
- C4 revocation: **signed lists only** (Corrector A1 — in-process verify; no fail-open), C5 audit, C6 rate limits
- N1: `--heartbeat-hz` capped at 2
- N3: `--skip-revoke` / `--no-interval-check` are **dev-only** — refused (exit 2, audited `refuse`) unless `LDTT_DEV=1`; when used, every skip is audited (`revocation_check` `skipped_dev` / `interval_skipped_dev`) and the session is marked `evidence_eligible: false`. Evidence never uses them (`scripts/check_evidence_no_dev_flags.py`).

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python scripts/validate_ldtt_yaml.py

# Spec v0.1.4 relative list_url is default in ldtt.yaml
python -m ldtt_ref_mav_observer \
  --cosign-key placeholders/keys/ldtt-placeholder.pub \
  --connection udpin:127.0.0.1:14550
```

### Release artifact (E3 / C3)

```bash
scripts/build_release.sh          # reproducible wheel (SOURCE_DATE_EPOCH pinned) -> dist/ + sha256
SOURCE_COMMIT=<public sha> scripts/sign_release.sh   # placeholder-key cosign sign + SLSA v1 provenance (draft)
```

CI workflow: `ci/ldtt-ref-mav-observer-ci.yml` (belongs at repo-root `.github/workflows/`; not active until a token with `workflow` scope pushes it).

### Real SITL smoke (E8) — no Docker

```bash
python scripts/real_sitl_smoke.py            # --backend official (default)
```

### Fake-peer smoke — interim E8 only, NOT SITL

```bash
python scripts/sitl_smoke.py
```

See `placeholders/README.md` and `ARCHITECTURE.md` §4 / §7.

## License

Apache-2.0 (connector). pymavlink LGPL-3.0 — see `sbom.spdx.json`.

---
*Phase 2 draft · Linked Drone Tool Trust · connector stamp only; not aircraft certification; no FAA claims.*
