# Publish steps — https://github.com/rockmed888-ship-it/ldtt (Phase 2 frozen)

Canonical repo (P7, locked): **rockmed888-ship-it/ldtt**.
**Phase 2 freeze: PASS** (Corrector). Connector/stamp **0.1.0** remains a **draft/placeholder stamp**, not a real trust-root stamp.

## Live on main (2026-10-06 CT)

| Path | Status |
|---|---|
| `revocations/revocations.json` | published — empty list, `list_version` **3**, `issued_at` 2026-10-06T10:41:27Z, `ldtt_spec` **0.1.4** (N4), placeholder-key signed |
| `revocations/revocations.json.sigstore.json` | published (cosign sign-blob, placeholder key, Rekor-logged) |
| `stamps/org.ldtt.ref-mav-observer/0.1.0.json` | published **draft/placeholder** — real wheel digest `sha256:1c8c29dbc9d0638d2a8ad4e5b703c0f408e07fd06c938606be6b660ac14de6b5`, known_limitations C3 + C9, `issued_at` 2026-10-06T10:41:27Z, `ldtt_spec` **0.1.4** (N4) — **NOT** a real trust-root stamp |
| `stamps/org.ldtt.ref-mav-observer/0.1.0.json.sigstore.json` | published (placeholder key, Rekor-logged) |

Connector copies under `ref-connectors/ldtt-ref-mav-observer/placeholders/` are byte-identical.

Raw HTTPS (for future `list_url` flip):
`https://raw.githubusercontent.com/rockmed888-ship-it/ldtt/main/revocations/revocations.json`

Connector currently uses Spec v0.1.4 **relative** path per Corrector N2.

## Recurring: revocation list re-sign

`max_staleness_s` = 86400. Re-sign at least every 24 h (next due before **2026-10-07 05:41 CT** = 2026-10-07T10:41:27Z):
1. Set `issued_at` to now (UTC), bump `list_version` by 1 (never decrease; next = 4). Keep `ldtt_spec` **0.1.4** (N4 done).
2. `cosign sign-blob --yes --key placeholders/keys/ldtt-placeholder.key --bundle revocations/revocations.json.sigstore.json revocations/revocations.json`
3. Verify (`cosign verify-blob --key …/ldtt-placeholder.pub` and in-process `verified_local_key`), copy to `placeholders/revocations/`, push (no force-push).

## Next (PLAN REF, not done)

1. **P5:** CI keyless sign + GitHub SLSA attestation (workflow at `ci/ldtt-ref-mav-observer-ci.yml`; needs `workflow` scope to live under `.github/workflows/`)
2. **P6:** Trust root: issuer key or keyless identity before any **real** stamp
3. ~~N4~~ **DONE** 2026-10-06 ~05:41 CT: `list_version` 3, `ldtt_spec` 0.1.4 on stamp + revocations, both re-signed (placeholder key)
4. Optionally flip connector `list_url` to the raw HTTPS URL

Never publish `placeholders/keys/ldtt-placeholder.key`.
