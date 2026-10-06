# STATUS — ldtt-ref-mav-observer (Phase 2)

**Brand:** Linked Drone Tool Trust · **Lead:** creator · Corrector reviews via creator
**Tag:** Phase 2 · **Drafts only — not final**

Updated: 2026-10-06 ~04:35 America/Chicago (CT)

## Corrector A1 — FIXED (draft); A1-r — FIXED (draft, this turn)

| Item | Before | After |
|---|---|---|
| Missing cosign / verify fail | Observe **fail-open**: load unsigned list (`cosign_missing_fail_open`) | **Never load unsigned list.** Treat as list-unreachable: keep last **verified** list until `max_staleness_s`, then fail closed (warn + refuse sessions / halt; no egress to stop) |
| Rollback (`list_version`↓) | Kept prior list and continued (not fail-closed) — flagged in STATUS | **Fail closed** (`rollback_rejected` + `is_fail_closed`); warn + refuse sessions / halt |
| C4 `known_limitations` waive | Waived signed-list when cosign missing | **Removed** — no C4 waiver |
| Verify path | Shell `cosign` primary; fail-open if missing | **In-process:** `cryptography` for local-key cosign bundles; `sigstore-python` for Fulcio Bundle JSON; cosign CLI optional fallback only |
| **A1-r** disk cache | `save_cache` re-`json.dumps`; `load_cache` set `has_verified_list` with **no** re-verify / no rollback | **`save_cache`:** original body bytes + sibling `.sigstore.json`. **`load_cache`:** re-run `verify_fn` (ignore on fail); apply `list_version` rollback. Tampered cache → `unreachable_no_cache` / fail closed. `__main__` sets `verify_fn` before `load_cache`. |

## N1 / N2 / N3

| Item | Status |
|---|---|
| N1 `--heartbeat-hz` ≤ 2 | Enforced in `__main__` (`HEARTBEAT_HZ_MAX=2.0`); tests in `test_heartbeat_hz_cap.py` |
| N2 `list_url` relative + schema 0.1.4 | `ldtt_spec: "0.1.4"`; `list_url: placeholders/revocations/revocations.json` |
| **N3** dev-only skip flags | `--skip-revoke` / `--no-interval-check` require `LDTT_DEV=1` (exact). Else exit 2 + audit `refuse` (`dev_only_flag_without_dev_mode`). With it: WARN, `session` marked `dev_mode/evidence_eligible:false`, audit `revocation_check` `skipped_dev` / `interval_skipped_dev`. Env gate chosen over a stripped build (one wheel = one digest). `scripts/check_evidence_no_dev_flags.py` + test keep evidence clean; pre-N3 runs moved to `evidence/superseded-dev-flags/`. 12 tests in `tests/test_n3_dev_flags.py`. See `evidence/e6-n3-dev-flag-gate.md`. |

## Public repo

**https://github.com/rockmed888-ship-it/ldtt** (live; full Spec v0.1.4 + schema on main). `connector.source_url` points here.

| Path | Live? |
|---|---|
| `LDTT-Stamp-Spec-v0.1.4.md`, `schema/ldtt.schema.json`, `schema/test_schema.py` | Yes (byte-identical to local) |
| `revocations/revocations.json` + `.sigstore.json` | Yes (placeholder-key signed empty list, `issued_at` 2026-10-06T08:42Z) |
| `stamps/org.ldtt.ref-mav-observer/0.1.0.json` + `.sigstore.json` | Yes (digest still zeros — re-issuing the stamp is for creator/Corrector, not done) |
| `ref-connectors/ldtt-ref-mav-observer/` | Synced this turn (N3 + E3), see final commit in report |
| `.github/workflows/` | **Not pushed** — gh token scopes `repo, gist, read:org` lack `workflow`. Copy at `ci/ldtt-ref-mav-observer-ci.yml`. |

Older note: dustindent9-cmyk/ldtt was the previous target (incomplete); Spec/schema were also pushed there earlier this turn before the switch. No further pushes there.

## SITL PASS — real ArduPilot SITL (draft evidence)

Re-run 2026-10-06 ~04:13 CT **without** dev-only flags (N3): real ArduCopter SITL V4.7.1, `evidence/e8-real-sitl-result.json` **17/17** (adds `no_dev_only_flags_n3`; `revocation_check_ran_cosign_verified` now accepts in-process `verified_local_key`). Fake-peer = interim E8 only.

## Evidence E2 / E3 / E4 / E6 (honest)

| ID | Status | Notes |
|---|---|---|
| E2 | ☑ draft | `sbom.spdx.json` hand-draft from venv pins. Not syft-generated. |
| E3 | ☐ partial (stronger) | **Real** reproducible wheel digest in `ldtt.yaml` (same on Py 3.12/3.13 and from clean `git archive` of the public commit). Wheel + cosign bundle + SLSA v1 statement + DSSE bundle in `dist/`, all **placeholder key**, local builder, Rekor-logged. Gaps: no issuer/keyless sig, no CI-built provenance (workflow not active), no hosted release. `evidence/e3-release-provenance.md`. |
| E4 | ☑ draft | `privacy.egress: []`; MAVLink-only TX on wire. |
| E6 | ☑ draft | A1 + A1-r + N3; `e6-revocation-pytest-output.txt` (28) with `LDTT_DEV` unset. |

## Tests

**57 passed** (pytest, 2026-10-06 CT; 1 skip only where cosign CLI absent). `ldtt.yaml` VALID vs schema v0.1.4.

## Remaining before Phase 2 freeze / Corrector

1. Activate CI: push `ci/ldtt-ref-mav-observer-ci.yml` to repo-root `.github/workflows/` with a `workflow`-scoped token → keyless sign + GitHub SLSA attestation + digest-match check.
2. Issuer decision: placeholder key vs keyless identity for lists/stamps/artifacts.
3. **Re-sign revocation list** before 2026-10-07 ~03:42 CT (`max_staleness_s` 86400) or connectors (and CI real-SITL) fail closed.
4. Re-issue stamp record with real digest (creator/Corrector call).
5. Corrector review of N3 + E3 (via creator).

## Confirmations

- Spend: **$0**
- Hardware: **none**
- Brand: **Linked Drone Tool Trust**
- Drafts only — **not final** / **not Phase 2 PASS**
