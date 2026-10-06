# Placeholders — stamps + revocations (Phase 2 draft, DoD #5)

**Brand:** Linked Drone Tool Trust · **Not final**

## Layout

```
placeholders/
  revocations/revocations.json
  revocations/revocations.json.sigstore.json
  stamps/org.ldtt.ref-mav-observer/0.1.0.json
  stamps/org.ldtt.ref-mav-observer/0.1.0.json.sigstore.json
  keys/ldtt-placeholder.pub          # public key for local verify
  keys/ldtt-placeholder.key          # PRIVATE — gitignored; local/dev only
```

## Runtime (Spec v0.1.4 relative list_url)

`ldtt.yaml` sets `revocation.list_url: placeholders/revocations/revocations.json`.
Overrides still work: `--revocation-list` / `LDTT_REVOCATION_LIST_PATH`.

Verify is **in-process** (cryptography for local-key bundles; sigstore-python for
Fulcio Bundle JSON). Cosign CLI is optional fallback only.

**Corrector A1:** never load an unsigned list. Missing/failed verify = list-unreachable
(keep last verified until `max_staleness_s`, then fail closed). No C4 fail-open waiver.

## Public repo (live Spec §5 copies)

https://github.com/dustindent9-cmyk/ldtt

```
revocations/revocations.json
revocations/revocations.json.sigstore.json
stamps/org.ldtt.ref-mav-observer/0.1.0.json
stamps/org.ldtt.ref-mav-observer/0.1.0.json.sigstore.json
```

When creator flips production URL:

`https://raw.githubusercontent.com/dustindent9-cmyk/ldtt/main/revocations/revocations.json`

Re-sign with **cosign keyless** from Actions after merge; never publish the private key.

## Local re-sign

```bash
export COSIGN_PASSWORD=
cosign sign-blob --yes --key placeholders/keys/ldtt-placeholder.key \
  --bundle placeholders/revocations/revocations.json.sigstore.json \
  placeholders/revocations/revocations.json
```

---
*Phase 2 draft · Linked Drone Tool Trust · drafts only — never call final/PASS*
