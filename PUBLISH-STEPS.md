# Publish steps — https://github.com/dustindent9-cmyk/ldtt (Phase 2 draft)

## Live on main (2026-10-06 CT)

| Path | Status |
|---|---|
| `revocations/revocations.json` | published (empty list, local-key signed) |
| `revocations/revocations.json.sigstore.json` | published |
| `stamps/org.ldtt.ref-mav-observer/0.1.0.json` | published (digest still placeholder zeros) |
| `stamps/org.ldtt.ref-mav-observer/0.1.0.json.sigstore.json` | published |

Raw HTTPS (for future `list_url` flip):
`https://raw.githubusercontent.com/dustindent9-cmyk/ldtt/main/revocations/revocations.json`

Connector currently uses Spec v0.1.4 **relative** path per Corrector N2.

## Next (not done this turn)

1. Re-sign with cosign keyless from Actions on `main`
2. First real release artifact + provenance (C3/E3)
3. Optionally flip connector `list_url` to the raw HTTPS URL

Never publish `placeholders/keys/ldtt-placeholder.key`.
