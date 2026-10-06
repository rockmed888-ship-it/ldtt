# LDTT Evidence Checklist (Spec v0.1.3/0.1.4) — ldtt-ref-mav-observer

**Phase 2 draft** (updated 2026-10-06 ~04:05 CT). **Not final.** Manifest `ldtt_spec: "0.1.4"`.

| Field | Value |
|---|---|
| Connector id | org.ldtt.ref-mav-observer |
| Version | 0.1.0 |
| Artifact digest (`sha256:`) | TBD (placeholder zeros in ldtt.yaml) |
| Level requested | observe |
| Transport | mavlink2 |
| Egress declared? | no |
| Holder contact | security@ldtt.example |
| Date | 2026-10-06 |
| Public repo | https://github.com/dustindent9-cmyk/ldtt |

## Evidence

| ID | Evidence | Applies | Link to file(s) | Done |
|---|---|:-:|---|:-:|
| E1 | `ldtt.yaml` passes schema | O P C | `evidence/e1-validate-output.txt` (0.1.4 VALID) | ☑ draft |
| E2 | SPDX + SBOM (C1) | O P C | Apache-2.0; `sbom.spdx.json` hand-draft from venv pins (incl. sigstore/cryptography). Not syft. | ☑ draft |
| E3 | Signed artifact + provenance (C3) | O P C | Empty revocation + stamp record local-key signed; live at repo Spec §5 paths. **No** release artifact digest/provenance yet. | ☐ partial |
| E4 | Privacy / no undeclared egress (C2) | O P C | `privacy.egress: []`; no egress client in src; real-SITL wire capture = MAVLink-only TX (HEARTBEAT + COMMAND_LONG 511/512). Strengthened writeup in ARCHITECTURE §3. | ☑ draft |
| E5 | Sample audit log (C5) | O P C | Real SITL + refuse audits under `evidence/` | ☑ draft |
| E6 | Revocation tests (C4) **A1** | O P C | `tests/test_revocation.py` (incl. unsigned-never-load, rollback fail-closed); `tests/test_cosign_and_locks.py` (in-process local-key verify; no fail-open) | ☑ draft |
| E7 | Rate-limit (C6) | O P C | prior tests + heartbeat exempt + N1 cap tests | ☑ draft |
| E8 | SITL allowlists | O P C | Real SITL V4.7.1 evidence (prior turn); not re-run this turn | ☑ draft |
| E9–E12 | Higher levels | P/C | N/A at Observe | ☐ N/A |

## Known limitations

| Control | Note |
|---|---|
| C3 | Build digest/signature/provenance placeholders until first CI-signed release |
| C4 | **No waiver.** Signed list required. Verify in-process (cryptography / sigstore-python); cosign CLI optional. Public HTTPS list available; connector uses relative path per N2 until creator flips. |
| C9 | Observe: mavlink signing false |
| E8 | Real SITL = ArduCopter V4.7.1 official prebuilt; PX4 not run; fake-peer interim only |

## Holder attestation

Name / handle: ______________ Date: __________  (**TBD — do not sign as final**)

*LDTT is a connector stamp only. It does not certify aircraft, operators, or flight safety, and makes no FAA or other regulatory claim.*
