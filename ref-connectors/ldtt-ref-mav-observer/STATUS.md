# STATUS — ldtt-ref-mav-observer (Phase 2)

**Brand:** Linked Drone Tool Trust · **Lead:** creator · Corrector reviews via creator
**Tag:** Phase 2 · **Drafts only — not final**

Updated: 2026-10-06 ~04:10 America/Chicago (CT)

## Corrector A1 — FIXED (draft); A1-r — FIXED (draft, this turn)

| Item | Before | After |
|---|---|---|
| Missing cosign / verify fail | Observe **fail-open**: load unsigned list (`cosign_missing_fail_open`) | **Never load unsigned list.** Treat as list-unreachable: keep last **verified** list until `max_staleness_s`, then fail closed (warn + refuse sessions / halt; no egress to stop) |
| Rollback (`list_version`↓) | Kept prior list and continued (not fail-closed) — flagged in STATUS | **Fail closed** (`rollback_rejected` + `is_fail_closed`); warn + refuse sessions / halt |
| C4 `known_limitations` waive | Waived signed-list when cosign missing | **Removed** — no C4 waiver |
| Verify path | Shell `cosign` primary; fail-open if missing | **In-process:** `cryptography` for local-key cosign bundles; `sigstore-python` for Fulcio Bundle JSON; cosign CLI optional fallback only |
| **A1-r** disk cache | `save_cache` re-`json.dumps`; `load_cache` set `has_verified_list` with **no** re-verify / no rollback | **`save_cache`:** original body bytes + sibling `.sigstore.json`. **`load_cache`:** re-run `verify_fn` (ignore on fail); apply `list_version` rollback. Tampered cache → `unreachable_no_cache` / fail closed. `__main__` sets `verify_fn` before `load_cache`. |

## N1 / N2

| Item | Status |
|---|---|
| N1 `--heartbeat-hz` ≤ 2 | Enforced in `__main__` (`HEARTBEAT_HZ_MAX=2.0`); tests in `test_heartbeat_hz_cap.py` |
| N2 `list_url` relative + schema 0.1.4 | `ldtt_spec: "0.1.4"`; `list_url: placeholders/revocations/revocations.json` (schema widen PASS) |

## Public repo

**https://github.com/dustindent9-cmyk/ldtt**

| Path | Live? |
|---|---|
| `revocations/revocations.json` + `.sigstore.json` | Yes (pushed this turn; local-key signed empty list) |
| `stamps/org.ldtt.ref-mav-observer/0.1.0.json` + `.sigstore.json` | Yes (local-key; digest still placeholder zeros) |
| Future HTTPS list_url | `https://raw.githubusercontent.com/dustindent9-cmyk/ldtt/main/revocations/revocations.json` (connector still uses relative per N2 until creator flips) |

`connector.source_url` → `https://github.com/dustindent9-cmyk/ldtt`

## SITL PASS — real ArduPilot SITL (prior draft evidence)

**SITL PASS** — real ArduCopter SITL V4.7.1 (`evidence/e8-real-sitl-result.json`, 16/16). **Not re-run this turn:** C4 changes are unit-covered; smoke still uses local signed placeholders + in-process verify (same signed files). Re-run real SITL only if Corrector asks. Fake-peer = interim E8 only.

## Evidence E2 / E3 / E4 / E6 (honest)

| ID | Status | Notes |
|---|---|---|
| E2 | ☑ draft | `sbom.spdx.json` hand-draft from venv pins (pymavlink 2.4.50, sigstore 3.6.7, …). Not syft-generated. |
| E3 | ☐ partial | Stamp + empty revocation **local-key** signed blobs live on public repo Spec §5 paths. **No** signed release artifact / SLSA provenance / real digest yet (C3 known_limitation). |
| E4 | ☑ draft | `privacy.egress: []`; no egress client in src; wire capture shows MAVLink-only TX. No host-wide pcap. |
| E6 | ☑ draft | Tests for **A1** + **A1-r**: no unsigned load; cosign-missing = unreachable; rollback fail-closed; tampered cache ignored. See `tests/test_revocation.py`, `tests/test_cosign_and_locks.py`. |

## Tests

**45 passed** (pytest, 2026-10-06 CT). `ldtt.yaml` VALID vs schema v0.1.4. Includes A1-r tampered-cache test.

## Confirmations

- Spend: **$0**
- Hardware: **none**
- Brand: **Linked Drone Tool Trust**
- Drafts only — **not final** / **not Phase 2 PASS**
