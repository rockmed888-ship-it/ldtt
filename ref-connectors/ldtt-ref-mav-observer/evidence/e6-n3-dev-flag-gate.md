# E6 supplement — N3 dev-only flag gate (Phase 2 draft, not final)

Updated 2026-10-06 ~04:30 CT. Corrector N3.

| Item | Behavior |
|---|---|
| Gate | `--skip-revoke`, `--no-interval-check` need env `LDTT_DEV=1` (exact value; `0`/`true`/empty refused). Code: `src/ldtt_ref_mav_observer/dev_flags.py`, `__main__.py`. |
| Without gate | Exit **2**; stderr `REFUSED ... dev-only`; audit `{"event":"refuse","reason":"dev_only_flag_without_dev_mode","flags":[...]}`; no `session`/`revocation_check` written. |
| With gate | stderr WARN; `session start` has `dev_mode:true, evidence_eligible:false, dev_flags:[...]`; audit `revocation_check outcome:"skipped_dev"` (startup, `--skip-revoke`) and `outcome:"interval_skipped_dev"` (interval; also implied by `--skip-revoke`). `--no-interval-check` alone still runs + audits the verified startup check. |
| Why env gate, not stripped build | One release wheel = one digest (C3). A second "release" build without the flags would be a different artifact. |
| Evidence rule | E5/E6/E8 evidence comes only from runs without these flags. `scripts/check_evidence_no_dev_flags.py` scans `evidence/` (excl. `superseded-dev-flags/`) for skip outcomes, `dev_mode:true`, or the flags on recorded command lines; runs in CI and in `tests/test_n3_dev_flags.py::test_repo_evidence_does_not_rely_on_skip_flags`. |
| Regenerated | `e6-revocation-pytest-output.txt` (LDTT_DEV unset), `e7-locks-pytest-output.txt`, `e5-real-sitl-audit.jsonl` + `e8-real-sitl-*` (real ArduCopter V4.7.1, no dev flags, 17/17), `e5-sample-audit.jsonl` + `e8-smoke-result.json` (fake peer, interim). Old runs that used `--no-interval-check` → `superseded-dev-flags/`. |

Tests (`tests/test_n3_dev_flags.py`, 12): exact-value gate; refusal per flag (audited, exit 2); wrong env values refused;
skip-revoke audits both skips + session marked; no-interval-check audits interval skip while startup verifies `ok`;
release run has no dev markers; checker flags skip runs and ignores the superseded dir; in-tree evidence clean.
N3 tests use an ephemeral P-256 key + fresh signed list so they don't depend on the published list's staleness.
