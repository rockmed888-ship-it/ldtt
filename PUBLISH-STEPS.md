# Publish steps — https://github.com/rockmed888-ship-it/ldtt (Phase 2 frozen)

Canonical repo (P7, locked): **rockmed888-ship-it/ldtt**.
**Phase 2 freeze: PASS** (Corrector). Connector/stamp **0.1.0** remains a **draft/placeholder stamp**, not a real trust-root stamp.

## Live on main (2026-10-06 CT)

| Path | Status |
|---|---|
| `revocations/revocations.json` | published — empty list, `list_version` **8**, `issued_at` 2026-10-07T14:18:41Z (09:18 CT), `ldtt_spec` **0.1.4**, placeholder-key signed (24 h ops re-sign; was v7 @ 13:46:51Z) |
| `revocations/revocations.json.sigstore.json` | published (cosign sign-blob, placeholder key, Rekor-logged) |
| `stamps/org.ldtt.ref-mav-observer/0.1.0.json` | published **draft/placeholder** — real wheel digest `sha256:1c8c29dbc9d0638d2a8ad4e5b703c0f408e07fd06c938606be6b660ac14de6b5`, known_limitations C3 + C9, `issued_at` 2026-10-06T10:41:27Z, `ldtt_spec` **0.1.4** (N4) — **NOT** a real trust-root stamp |
| `stamps/org.ldtt.ref-mav-observer/0.1.0.json.sigstore.json` | published (placeholder key, Rekor-logged) |

Connector copies under `ref-connectors/ldtt-ref-mav-observer/placeholders/` are byte-identical (list v8: json sha256 `8ab49721…238f`, bundle `6c6ff17f…5f7d`).

Raw HTTPS (for future `list_url` flip):
`https://raw.githubusercontent.com/rockmed888-ship-it/ldtt/main/revocations/revocations.json`

Connector currently uses Spec v0.1.4 **relative** path per Corrector N2.

## Recurring: revocation list re-sign

`max_staleness_s` = 86400. Re-sign at least every 24 h (next due before **2026-10-08 09:18 CT** = 2026-10-08T14:18:41Z):
1. Set `issued_at` to now (UTC), bump `list_version` by 1 (never decrease; next = 9). Keep `ldtt_spec` **0.1.4** (N4 done).

Log: v3 2026-10-06T10:41:27Z (N4, `d65b4ed`) → v4 2026-10-06T12:12:10Z (07:12 CT) → v5 2026-10-06T14:14:41Z (09:14 CT) → v6 2026-10-06T17:18:41Z (12:18 CT) → v7 2026-10-07T13:46:51Z (08:46 CT) → **v8 2026-10-07T14:18:41Z** (09:18 CT signed, published after Lead OK ~2 PM CT; ops re-sign, Rekor 3132708103, revoked `[]`; stamp `0.1.0` not re-signed — no stamp field depends on the list).
2. `cosign sign-blob --yes --key placeholders/keys/ldtt-placeholder.key --bundle revocations/revocations.json.sigstore.json revocations/revocations.json`
3. Verify (`cosign verify-blob --key …/ldtt-placeholder.pub` and in-process `verified_local_key`), copy to `placeholders/revocations/`, push (no force-push).

## Next (PLAN REF, not done)

1. **P5:** CI keyless sign + GitHub SLSA attestation (workflow at `ci/ldtt-ref-mav-observer-ci.yml`; needs `workflow` scope to live under `.github/workflows/`)
2. **P6:** Trust root: issuer key or keyless identity before any **real** stamp
3. ~~N4~~ **DONE** 2026-10-06 ~05:41 CT: `list_version` 3, `ldtt_spec` 0.1.4 on stamp + revocations, both re-signed (placeholder key)
4. Optionally flip connector `list_url` to the raw HTTPS URL

Never publish `placeholders/keys/ldtt-placeholder.key`.
