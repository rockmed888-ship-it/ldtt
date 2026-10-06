# E3 (C3) — release artifact, signature, provenance (Phase 2 DRAFT, not final)

Updated 2026-10-06 ~04:40 CT. $0, free tools only (setuptools/build, cosign v2, public Rekor).

| Piece | Value / file | Honest status |
|---|---|---|
| Artifact | `dist/ldtt_ref_mav_observer-0.1.0-py3-none-any.whl` (wheel; sdist not reproducible → not a release artifact) | real |
| Digest | `sha256:1c8c29dbc9d0638d2a8ad4e5b703c0f408e07fd06c938606be6b660ac14de6b5` = `ldtt.yaml` `build.artifact_digest` = `dist/SHA256SUMS` | real, **reproducible**: same bytes from Py 3.12 and 3.13, and from a clean `git archive` of the source commit |
| Source commit | `fe1e34ec2e454bde55d130c606a601b065d3ce84` on https://github.com/rockmed888-ship-it/ldtt (`build.source_commit`) | public |
| Signature | `dist/ldtt-ref-mav-observer.sigstore.json` (cosign `sign-blob`, Rekor logIndex 3106383067) | **placeholder key** (`placeholders/keys/ldtt-placeholder.pub`), not issuer/keyless |
| Provenance | `dist/provenance.intoto.jsonl` (in-toto Statement, predicateType `https://slsa.dev/provenance/v1`, subject = wheel digest, source = commit above); DSSE signature bundle `dist/provenance.intoto.sigstore.json` (Rekor logIndex 3106383127) | **local builder** (`https://ldtt.example/builders/local-draft-box`), placeholder key → not SLSA L2+ |
| CI path | `ci/ldtt-ref-mav-observer-ci.yml`: rebuild + digest==ldtt.yaml check, keyless `cosign sign-blob`, `actions/attest-build-provenance@v2` | **not active**: must live at repo-root `.github/workflows/`; current gh token lacks `workflow` scope |

## Verify (anyone, $0)

```bash
git clone https://github.com/rockmed888-ship-it/ldtt && cd ldtt && git checkout fe1e34ec2e454bde55d130c606a601b065d3ce84
cd ref-connectors/ldtt-ref-mav-observer && pip install build && PYTHON=python scripts/build_release.sh   # -> sha256:1c8c29db...
cosign verify-blob --key placeholders/keys/ldtt-placeholder.pub --bundle dist/ldtt-ref-mav-observer.sigstore.json dist/*.whl
cosign verify-blob-attestation --key placeholders/keys/ldtt-placeholder.pub --type slsaprovenance1 \
  --bundle dist/provenance.intoto.sigstore.json dist/*.whl
```
(Signature/provenance files are on main in the commit after `fe1e34e`; the wheel bytes rebuild identically.)

## Gaps (C3 known_limitation stays)

1. Signer is the placeholder key, not an issuer key or keyless CI identity.
2. Provenance is self-generated on a local box, not by a hosted builder.
3. CI workflow not active (token scope).
4. No hosted release asset / tag; wheel lives in `dist/` on main.
5. Published stamp record still has the zero digest (re-issue = creator/Corrector decision).
