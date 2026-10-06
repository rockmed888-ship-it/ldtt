# LDTT Evidence Checklist (Spec v0.1.3/0.1.4) — ldtt-ref-mav-observer

**Phase 2 draft** (updated 2026-10-06 ~04:40 CT). **Not final.** Manifest `ldtt_spec: "0.1.4"`.

| Field | Value |
|---|---|
| Connector id | org.ldtt.ref-mav-observer |
| Version | 0.1.0 |
| Artifact digest (`sha256:`) | real, reproducible wheel digest in `ldtt.yaml` `build.artifact_digest` (see `evidence/e3-release-provenance.md`) |
| Level requested | observe |
| Transport | mavlink2 |
| Egress declared? | no |
| Holder contact | security@ldtt.example |
| Date | 2026-10-06 |
| Public repo | https://github.com/rockmed888-ship-it/ldtt |

## Evidence

| ID | Evidence | Applies | Link to file(s) | Done |
|---|---|:-:|---|:-:|
| E1 | `ldtt.yaml` passes schema | O P C | `evidence/e1-validate-output.txt` (0.1.4 VALID) | ☑ draft |
| E2 | SPDX + SBOM (C1) | O P C | Apache-2.0; `sbom.spdx.json` hand-draft from venv pins (incl. sigstore/cryptography). Not syft. | ☑ draft |
| E3 | Signed artifact + provenance (C3) | O P C | `dist/ldtt_ref_mav_observer-0.1.0-py3-none-any.whl` (reproducible; digest = ldtt.yaml); `dist/ldtt-ref-mav-observer.sigstore.json` (cosign sign-blob, **placeholder key**, Rekor-logged); `dist/provenance.intoto.jsonl` + `dist/provenance.intoto.sigstore.json` (SLSA v1 statement, DSSE, placeholder key, **local builder**) bound to public `source_commit`. Gaps: not issuer/keyless; not CI-built; CI workflow not active (token lacks `workflow` scope); no hosted release asset. `evidence/e3-release-provenance.md` | ☐ partial (draft, stronger) |
| E4 | Privacy / no undeclared egress (C2) | O P C | `privacy.egress: []`; no egress client in src; real-SITL wire capture = MAVLink-only TX (HEARTBEAT + COMMAND_LONG 511/512). Strengthened writeup in ARCHITECTURE §3. | ☑ draft |
| E5 | Sample audit log (C5) | O P C | `e5-real-sitl-audit.jsonl` (real SITL, **no dev-only flags**, regenerated post-N3) + refuse audits | ☑ draft |
| E6 | Revocation tests (C4) **A1 + N3** | O P C | `e6-revocation-pytest-output.txt` (28 tests, `LDTT_DEV` unset): `test_revocation.py`, `test_cosign_and_locks.py`, `test_n3_dev_flags.py`; `e6-n3-dev-flag-gate.md`. Evidence never uses `--skip-revoke`/`--no-interval-check` (gate script). Pre-N3 runs → `superseded-dev-flags/` | ☑ draft |
| E7 | Rate-limit (C6) | O P C | `e7-locks-pytest-output.txt` (29 tests, regenerated) | ☑ draft |
| E8 | SITL allowlists | O P C | Real ArduCopter SITL V4.7.1 re-run 2026-10-06 ~04:13 CT **without** dev flags: `e8-real-sitl-result.json` 17/17 (incl. `no_dev_only_flags_n3`) | ☑ draft |
| E9–E12 | Higher levels | P/C | N/A at Observe | ☐ N/A |

## Known limitations

| Control | Note |
|---|---|
| C3 | Real reproducible digest + placeholder-key signature + local SLSA statement. Issuer/keyless signing, CI-built provenance and hosted release still pending. |
| C9 | Observe: mavlink signing false |

These match `ldtt.yaml` `known_limitations` and the stamp record exactly (C3, C9 only). **C4 has no known_limitation / no waiver** (Corrector A1).

## C4 operations (not a limitation)

Signed list required; verify in-process (cryptography / sigstore-python), cosign CLI optional fallback only. Connector uses relative `list_url` per N2; public HTTPS copy on https://github.com/rockmed888-ship-it/ldtt. N3: dev-only skip flags gated by `LDTT_DEV=1` and audited. Published list `list_version` 2, `issued_at` 2026-10-06T09:30:33Z (placeholder-key re-sign) → must be re-signed before 2026-10-07 ~04:30 CT (`max_staleness_s` 86400) or connectors fail closed.

## Stamp record (draft)

`stamps/org.ldtt.ref-mav-observer/0.1.0.json` re-issued 2026-10-06T09:30:33Z with real wheel digest `sha256:1c8c29db…6b5`, `known_limitations` C3 + C9, placeholder-key signature (verifies in-process). Draft only, not a real stamp.

## Holder attestation

Name / handle: ______________ Date: __________  (**TBD — do not sign as final**)

*LDTT is a connector stamp only. It does not certify aircraft, operators, or flight safety, and makes no FAA or other regulatory claim.*
