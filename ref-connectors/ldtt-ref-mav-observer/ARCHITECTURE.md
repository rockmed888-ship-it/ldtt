# Architecture — ldtt-ref-mav-observer (Phase 2 Draft)

**LDTT = Linked Drone Tool Trust** · Phase 2 · Observe reference connector  
**Status:** Architecture draft for creator / Corrector review — **not final**  
**Level:** Observe · **Scope:** `observe:telemetry` only · **Transport:** mavlink2  
**Stack:** Python 3.11+ + pymavlink (LGPL-3.0) · real ArduCopter SITL (official prebuilt binary, no Docker) for E8; fake HEARTBEAT peer = interim only · $0 tooling

> Connector stamp only. Not aircraft certification. No FAA claims. No hardware required.

---

## 1. Goals and non-goals

**Goals**
- Read-only MAVLink 2 telemetry observer stamped at Observe.
- Enforce C4 (revocation + cosign when available), C5 (audit log), C6 (rate limits) in-process.
- Local display only (CLI); no egress; retention_days 0.
- Public git https://github.com/rockmed888-ship-it/ldtt + free CI + in-process verify + cosign keyless path.

**Non-goals (Phase 2)**
- Operate/Command levels, MCP transport, vendor APIs, live flight, DJI reverse engineering.
- Operate tx widening (candidates in mapping draft only).
- Calling any deliverable “final” or “PASS” — Corrector reviews via creator.

---

## 2. Modules

```
src/ldtt_ref_mav_observer/
  __main__.py           # CLI: load ldtt.yaml → cosign+revoke → connect → display
  allowlist.py          # RX/TX/command gates; LOCKED_OUT_TX (REQUEST_DATA_STREAM, LOG_REQUEST_*)
  mavlink_client.py     # pymavlink connection; rx filter; tx gate before every send
  stream_setup.py       # MAV_CMD_REQUEST_MESSAGE + MAV_CMD_SET_MESSAGE_INTERVAL only
  rate_limiter.py       # Token-bucket for reads_per_s (C6)
  audit_log.py          # Append-only JSONL writer (C5)
  revocation_checker.py # Signed list; max_staleness_s; list_version rollback (C4)
  cosign_verify.py      # cosign verify-blob wrapper (startup + interval)
  cli.py                # Local terminal telemetry display (no network egress)
  config.py             # Load + validate ldtt.yaml against schema
```

| Module | Responsibility | Spec control |
|---|---|---|
| `allowlist` | Deny TX not in connector Observe set; hard-deny `REQUEST_DATA_STREAM` + `LOG_REQUEST_*`; COMMAND_LONG only `{REQUEST_MESSAGE, SET_MESSAGE_INTERVAL}` | §4, F8, creator locks |
| `mavlink_client` | UDP/TCP/serial; drop RX outside `rx_allowlist`; never send without allowlist+rate check | E8 |
| `stream_setup` | Request telemetry via the two read cmds only (PX4-friendly; no REQUEST_DATA_STREAM) | Handoff / F8 |
| `rate_limiter` | Cap outbound request rate at `rate_limits.reads_per_s`; **HEARTBEAT TX exempt** (keepalive, `EXEMPT_TX`) | C6, creator lock #2 |
| `audit_log` | Session, scope_grant, egress_opt_in, revocation_check (= **minimum** set); `refuse`/`deny` always writable | C5, creator lock #3 |
| `revocation_checker` | Startup + every `check_interval_s`; fail-closed past `max_staleness_s`; reject lower `list_version` | C4, §5.2 |
| `cosign_verify` | In-process verify (cryptography local-key; sigstore-python Bundle); cosign CLI optional; **never** fail-open | Corrector A1 |
| `cli` | Print filtered telemetry to stdout; no file retention of vehicle data beyond session | C2 |

**Why pymavlink over MAVSDK-Python:** Observe needs message-level RX/TX allowlists and COMMAND_LONG command gating. License: LGPL-3.0 (compatible with Apache-2.0 connector with dynamic linking notes in SBOM).

---

## 3. Data flow

```
┌─────────────┐   MAVLink 2    ┌──────────────────┐
│ ArduPilot / │◄──────────────►│  mavlink_client  │
│ PX4 SITL or │   (local only) │  + allowlist     │
│ fake peer   │                │  + rate_limiter  │
└─────────────┘                └────────┬─────────┘
                                        │ allowed RX msgs
                                        ▼
                               ┌──────────────────┐
                               │  cli (local UI)  │──► stdout only
                               └──────────────────┘

Startup / interval:
  cosign_verify ── in-process verify ──► revocations.json + .sigstore.json
  revocation_checker ── list_url (relative v0.1.4) or --revocation-list
       ├── revoked / stale / rollback → fail closed (Observe: warn + refuse sessions / halt)
       ├── verify missing/fail → treat as unreachable (last verified until max_staleness_s, else fail closed)
       └── ok / verified → continue
  Never load unsigned list contents (Corrector A1).
  All outcomes → audit_log (JSONL, local path)
```

**TX path (strict):** `want_send(msg)` → not in LOCKED_OUT_TX? → allowlist TX ok? → if COMMAND_LONG, command in allowlist? → rate_limiter allow (**skipped for HEARTBEAT only**) → send → audit `refuse` on failure.

**GCS keepalive:** `__main__` sends HEARTBEAT (MAV_TYPE_GCS) at `--heartbeat-hz` (default 1 Hz, **max 2** per N1) via `MavlinkClient.send_heartbeat()`. Allowlist-gated; exempt from `reads_per_s`.

**Privacy / E4:** `egress: []`, `personal_data: []`, `retention_days: 0`. No HTTP/cloud client in `src/` (revocation fetch is local relative path by default; HTTPS only if operator points `list_url` at a URL). CLI prints to stdout only. Audit log stores control events, not GPS tracks. Real-SITL wire capture (`evidence/e8-real-sitl-wire-capture.json`) shows TX confined to the MAVLink link (HEARTBEAT + COMMAND_LONG 511/512). Host-wide pcap/firewall egress test not run (draft gap).

---

## 4. Enforcing C4 / C5 / C6

### C4 Revocation + cosign (Corrector A1)
1. On startup (and every `check_interval_s`), fetch list + sibling `.sigstore.json`.
2. **list_url (v0.1.4):** relative path `placeholders/revocations/revocations.json` (N2). Public HTTPS also live: `https://raw.githubusercontent.com/rockmed888-ship-it/ldtt/main/revocations/revocations.json`.
3. **Verify in-process:** cryptography ECDSA for local-key cosign bundles; sigstore-python for Fulcio Bundle JSON; cosign CLI optional fallback. Default key: `placeholders/keys/ldtt-placeholder.pub`.
4. **Never load unsigned lists.** Missing/failed verify = unreachable: keep last verified list until `max_staleness_s`, then fail closed (warn + refuse sessions / halt). No C4 known_limitation waiver.
5. **Disk cache (A1-r):** `save_cache` writes **original body bytes** + sibling `.sigstore.json` (no re-`json.dumps`). `load_cache` re-runs `verify_fn` and ignores cache on verify failure; also applies `list_version` rollback. Tampered cache → treat as no cache → fail closed when list unreachable.
6. **Rollback / staleness / revoked:** fail closed (Observe: warn + halt; no egress to stop).
7. **N3 dev-only flags (`dev_flags.py`):** `--skip-revoke` / `--no-interval-check` are accepted only with env `LDTT_DEV=1` (exact). Otherwise: exit 2 + audit `refuse` (`reason: dev_only_flag_without_dev_mode`), no session started. With `LDTT_DEV=1`: stderr WARN; `session start` carries `dev_mode: true, evidence_eligible: false`; audit `revocation_check` `outcome: skipped_dev` (startup) and/or `interval_skipped_dev` (interval; implied by `--skip-revoke`). Chosen over stripping flags from release builds because one wheel = one digest (C3). `scripts/check_evidence_no_dev_flags.py` (CI + `tests/test_n3_dev_flags.py`) fails if any in-tree evidence contains skip outcomes / dev_mode / the flags; pre-N3 evidence moved to `evidence/superseded-dev-flags/`.

### C5 Audit log
JSONL at `audit_log.path` (or `--audit-path`). **Creator lock #3:** `audit_log.includes` (`session`, `scope_grant`, `egress_opt_in`, `revocation_check`) is the **minimum** set the connector must emit — not a filter. `refuse` (TX allowlist / rate refuse) and `deny` (policy deny, e.g. revocation fail-closed) are evidence-positive and are **always** writable even though they are not in the schema `includes` enum (`ALWAYS_ALLOWED_EVENTS`). The writer never drops an event for being absent from `includes`; `AuditLog.missing_required()` reports minimum-set events not yet written. Tests: `tests/test_audit_refuse.py`.

### C6 Rate limits
Token bucket on outbound requests at `reads_per_s` (capacity = refill = reads_per_s). **Creator lock #2:** GCS HEARTBEAT TX is a keepalive, not a read → **exempt** from the bucket (`rate_limiter.EXEMPT_TX = {"HEARTBEAT"}`); it consumes no tokens and is never rate-refused, but still must pass the TX allowlist. Every other TX (COMMAND_LONG REQUEST_MESSAGE / SET_MESSAGE_INTERVAL, PARAM_REQUEST_LIST) consumes 1 token. Tests: `tests/test_heartbeat_exempt.py`; real-link proof in `evidence/e8-real-sitl-result.json` (`heartbeat_exempt_on_real_link`).

---

## 5. SITL / smoke test plan (draft)

| ID | Test | How | Maps to |
|---|---|---|---|
| T1–T7 | Unit allowlist / rate / revocation | pytest | E6–E8 |
| T8 | **Real SITL smoke** | `scripts/real_sitl_smoke.py` — official ArduPilot prebuilt ArduCopter SITL (V4.7.1, `firmware.ardupilot.org/Copter/stable/SITL_x86_64_linux_gnu/`) on `tcp:127.0.0.1:5760`, no Docker. Phase A: observer CLI + wire capture. Phase B: negative TX on the same real link. 17 machine-checked criteria (incl. `no_dev_only_flags_n3`); re-run post-N3 **without** `--no-interval-check`. | E8 |
| T8b | Fake-peer smoke | `scripts/sitl_smoke.py` — pymavlink UDP HEARTBEAT peer. **Interim E8 only, never SITL PASS.** | E8 (interim) |
| T8c | dronekit-sitl copter-3.3 | Supplemental only: HEARTBEAT RX OK but 3.3 predates REQUEST_MESSAGE/SET_MESSAGE_INTERVAL → no stream ACK/telemetry; cannot meet criteria (`evidence/superseded-dev-flags/supplemental-dronekit-copter33/` — superseded: produced with `--no-interval-check`) | info |
| T9 | Schema | `ldtt.yaml` vs schema | E1 |
| T10 | Cosign | Local key verify placeholders; CI keyless | DoD #5 |

---

## 6. $0 CI / signing / provenance

| Piece | Free choice |
|---|---|
| CI | Repo-root `.github/workflows/ldtt-ref-mav-observer-ci.yml` (copy in `ci/`): pytest, schema, N3 evidence gate, in-process list/stamp verify; reproducible wheel + digest == `ldtt.yaml`; cosign keyless sign; `actions/attest-build-provenance` (SLSA v1, Sigstore); real SITL. **Not yet active** — gh token lacks `workflow` scope. |
| Build | `scripts/build_release.sh`: wheel only (sdist not reproducible), `SOURCE_DATE_EPOCH=1791244800`, pinned setuptools 84.0.0 / wheel 0.48.0; package readme = `README-pkg.md` so doc edits don't move the digest. Same digest on Py 3.12 + 3.13 and from a clean `git archive` of the public commit. |
| Sign | `scripts/sign_release.sh`: cosign `sign-blob` (placeholder key, Rekor-logged) → `dist/ldtt-ref-mav-observer.sigstore.json`; `attest-blob --type slsaprovenance1` → statement `dist/provenance.intoto.jsonl` + DSSE bundle `dist/provenance.intoto.sigstore.json`. Keyless + GitHub attestation = CI path. |
| Placeholders | `placeholders/` (copies of repo-root `revocations/`, `stamps/`) |

---

## 7. Risks and open questions — **updated for creator locks**

| # | Topic | Status after creator locks (Phase 2) |
|---|---|---|
| 1 | **Signed revocation lists (A1 / A1-r)** | **LOCKED (Corrector):** never load unsigned list; verify in-process; missing/fail = unreachable then fail closed. Disk cache re-verified (original bytes + bundle). No C4 waiver. |
| 2 | **REQUEST_DATA_STREAM** | **LOCKED:** REMOVED from ref connector `tx_allowlist` and enforcement (`LOCKED_OUT_TX`). Stream setup = REQUEST_MESSAGE + SET_MESSAGE_INTERVAL only (F8 / PX4-friendly). Schema may still list it for other connectors. |
| 3 | **HEARTBEAT as TX / rate** | **LOCKED (#2):** HEARTBEAT TX exempt from `reads_per_s` (keepalive, not a read). Still allowlist-gated. |
| 4 | **Audit of refused TX** | **LOCKED (#3):** `includes` = minimum set; `refuse`/`deny` always writable (evidence-positive). |
| 5 | **Revocation list_url** | **N2 DONE:** schema v0.1.4 relative path in `ldtt.yaml`. Public repo Spec §5 paths published on rockmed888-ship-it/ldtt. |
| 6 | **P4** | **LOCKED:** FLIGHTTERMINATION / REBOOT_SHUTDOWN / MOTOR_TEST = **Command** now; protect in **v0.2**. Geofence geometry upload OK at Operate; fence enable/disable barred. No schema change yet. |
| 7 | **Operate tx widening** | **LOCKED:** NO in Phase 2. Candidates in mapping draft only. |
| 8 | **Protected-settings** | Widen in **draft list** (`FENCE_*`, `GF_*`, `CBRK_*`, etc.). No schema bump unless asked. |
| 9 | LGPL pymavlink | Document in SBOM (draft `sbom.spdx.json`). |
| 10 | **LOG_REQUEST_*** | **LOCKED:** omitted from tx_allowlist + enforcement (scopes `observe:telemetry` only). |

Remaining open: C3 issuer/keyless signing + CI-built provenance (local draft done: real digest, placeholder-key signature + SLSA statement); activate CI (workflow scope); re-sign revocation list before `max_staleness_s` (list_version 2 issued 2026-10-06T09:30:33Z → stale after 2026-10-07 04:30 CT); optional flip of `list_url` to public HTTPS; keyless re-sign of published blobs via CI. Fake-peer smoke stays interim E8 only — never relabeled SITL PASS. **N1:** `--heartbeat-hz` ≤ 2. **N3:** dev-only skip flags gated + audited.

---

## 8. Phase 2 tagging

All docs and commits for this connector should be tagged **Phase 2**. Lead: creator. Corrector reviews finals via creator — **do not call this architecture or skeleton final.**

---
*LDTT Phase 2 draft · ldtt-ref-mav-observer · Linked Drone Tool Trust*
