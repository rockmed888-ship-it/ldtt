# STATUS — ldtt-ref-mav-observer (Phase 2)

**Brand:** Linked Drone Tool Trust · **Lead:** creator · Corrector reviews via creator
**Tag:** Phase 2 · **FROZEN** (Corrector freeze PASS)

Updated: 2026-10-06 ~05:45 America/Chicago (CT) — N4 revoke re-sign done

**Phase 2 freeze: PASS** (Corrector, via creator). Freeze scope unchanged. Connector artifacts remain drafts under that freeze.

**Corrector N3 + E3 review: PASS** (draft, via creator; `reviews/LDTT-v0.1.4-and-Phase2-arch-corrector-notes.md`). Preceded freeze.

### Stamp 0.1.0 = draft / placeholder only (not a real trust-root stamp)

`stamps/org.ldtt.ref-mav-observer/0.1.0` (and connector `placeholders/` copies) is a **draft/placeholder stamp** signed with the **placeholder local key**. It is **NOT** a real trust-root stamp: no LDTT issuer key, no keyless issuer identity, no production trust root (see P6 PLAN REF). Do not treat verify-success against the placeholder pubkey as a real stamp.

## Corrector A1 — FIXED (draft); A1-r — FIXED (draft)

| Item | Before | After |
|---|---|---|
| Missing cosign / verify fail | Observe **fail-open**: load unsigned list (`cosign_missing_fail_open`) | **Never load unsigned list.** Treat as list-unreachable: keep last **verified** list until `max_staleness_s`, then fail closed (warn + refuse sessions / halt; no egress to stop) |
| Rollback (`list_version`↓) | Kept prior list and continued (not fail-closed) — flagged in STATUS | **Fail closed** (`rollback_rejected` + `is_fail_closed`); warn + refuse sessions / halt |
| C4 `known_limitations` waive | Waived signed-list when cosign missing | **Removed** — no C4 waiver |
| Verify path | Shell `cosign` primary; fail-open if missing | **In-process:** `cryptography` for local-key cosign bundles; `sigstore-python` for Fulcio Bundle JSON; cosign CLI optional fallback only |
| **A1-r** disk cache | `save_cache` re-`json.dumps`; `load_cache` set `has_verified_list` with **no** re-verify / no rollback | **`save_cache`:** original body bytes + sibling `.sigstore.json`. **`load_cache`:** re-run `verify_fn` (ignore on fail); apply `list_version` rollback. Tampered cache → `unreachable_no_cache` / fail closed. `__main__` sets `verify_fn` before `load_cache`. |

## N1 / N2 / N3 (in freeze)

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
| `revocations/revocations.json` + `.sigstore.json` | Yes — placeholder-key signed: `list_version` **6**, `issued_at` **2026-10-06T17:18:41Z** (12:18 CT), empty list, `ldtt_spec` **0.1.4**. Verifies (cosign CLI `Verified OK` + in-process `verified_local_key`). Stale after **2026-10-07 12:18 CT** (2026-10-07T17:18:41Z). *(Ops re-sign 2026-10-06 12:18 CT, v5→v6; stamp `0.1.0` not re-signed — no field depends on the list.)* |
| `stamps/org.ldtt.ref-mav-observer/0.1.0.json` + `.sigstore.json` | Yes — **draft/placeholder stamp only** (not a real trust-root stamp): real wheel digest `sha256:1c8c29dbc9d0638d2a8ad4e5b703c0f408e07fd06c938606be6b660ac14de6b5`, `known_limitations` C3 + C9, `issued_at` 2026-10-06T10:41:27Z, `ldtt_spec` **0.1.4** (N4), placeholder-key signature (re-signed, verifies). |
| `ref-connectors/ldtt-ref-mav-observer/` | Synced through freeze-prep; this commit is STATUS freeze flip (N5) |
| `.github/workflows/` | **Not pushed** — gh token scopes `repo, gist, read:org` lack `workflow`. Copy at `ci/ldtt-ref-mav-observer-ci.yml`. **P5 stays PLAN REF.** |

**Canonical repo (P7, locked):** https://github.com/rockmed888-ship-it/ldtt only — `connector.source_url`, `list_url` HTTPS copy, provenance `source`/`buildType`, SBOM, docs. No other repo is referenced in config, provenance or docs.

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

## Post-freeze PLAN REF (not done — do not claim complete)

| Ref | Item | Status |
|---|---|---|
| **P5** | CI keyless sign + GitHub SLSA attestation + digest-match rebuild | **PLAN REF** — blocked on gh `workflow` scope. Workflow stays at `ci/ldtt-ref-mav-observer-ci.yml` (not under `.github/workflows/`). |
| **P6** | Trust root: placeholder key → LDTT issuer key (creator, §9.1) or keyless issuer identity; update connector verify config | **PLAN REF** — required before any **real** stamp. Placeholder local-key kept; honest C3 known_limitation. |
| P7 | Canonical repo locked: rockmed888-ship-it/ldtt | Done (under freeze). |
| **N4** | Revoke re-sign 2026-10-06 ~05:41 CT: `list_version` 2→**3**, `ldtt_spec` → **0.1.4** on stamp `0.1.0.json` **and** `revocations.json`, `issued_at` 2026-10-06T10:41:27Z; both re-signed with placeholder key, verified CLI + in-process; connector `placeholders/` mirrored. | **DONE** |
| Ops | Re-sign `revocations/revocations.json` (bump `list_version`, never decrease) | **Done 2026-10-06 12:18 CT:** `list_version` 5→**6**, `issued_at` 2026-10-06T17:18:41Z, revoked `[]`, placeholder key, CLI + in-process verified, `placeholders/` mirrored byte-identical. Next due before **2026-10-07 12:18 CT** (2026-10-07T17:18:41Z = issued_at + 86400 s); next `list_version` 7. |

## Confirmations

- Phase 2 freeze: **PASS** (Corrector) · status **frozen**
- Connector/stamp **0.1.0**: **draft/placeholder stamp only** — **NOT** a real trust-root stamp
- P5 / P6: **PLAN REF** (not done)
- N4: **done** (list_version 3, ldtt_spec 0.1.4 on stamp + revocations; placeholder key)
- Ops re-sign 2026-10-06 12:18 CT: revocations `list_version` **6** (issued 2026-10-06T17:18:41Z; stamp untouched). Next due before **2026-10-07 12:18 CT**.
- Spend: **$0**
- Hardware: **none**
- Brand: **Linked Drone Tool Trust**
