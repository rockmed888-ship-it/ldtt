# Superseded evidence — produced WITH dev-only flags (N3)

**Not evidence-eligible.** These runs passed `--no-interval-check` (now dev-only, `LDTT_DEV=1`, Corrector N3).
Kept only for history. Current E5/E8 evidence lives in `evidence/` and was regenerated
2026-10-06 ~04:13 CT on real ArduCopter SITL V4.7.1 **without** any dev-only flag (17/17 criteria).

- `real-sitl-v4.7.1-pre-n3/` — prior real-SITL run (pre-N3 command line had `--no-interval-check`).
- `supplemental-dronekit-copter33/` — dronekit copter-3.3 supplemental run (also had `--no-interval-check`).

`scripts/check_evidence_no_dev_flags.py` excludes this directory by design.
