#!/usr/bin/env bash
# E3 / C3 (Phase 2 DRAFT): sign the reproducible wheel + emit in-toto SLSA v1 provenance.
# Local path uses the PLACEHOLDER key (placeholders/keys/ldtt-placeholder.key, gitignored) — not an
# issuer key. CI (.github/workflows/ldtt-ref-mav-observer-ci.yml) adds keyless Fulcio signing and a
# GitHub SLSA build-provenance attestation once the workflow can be pushed.
# Usage: SOURCE_COMMIT=<sha> scripts/sign_release.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${SOURCE_COMMIT:?set SOURCE_COMMIT to the public commit holding the wheel inputs}"
REPO="${LDTT_REPO:-https://github.com/rockmed888-ship-it/ldtt}"
KEY="${COSIGN_KEY:-placeholders/keys/ldtt-placeholder.key}"
PUB="${COSIGN_PUB:-placeholders/keys/ldtt-placeholder.pub}"
COSIGN="${COSIGN:-$(command -v cosign || echo tools/cosign)}"
export COSIGN_PASSWORD="${COSIGN_PASSWORD:-}"
WHL=$(ls dist/ldtt_ref_mav_observer-*-py3-none-any.whl)
DIGEST=$(sha256sum "$WHL" | cut -d' ' -f1)
grep -q "sha256:$DIGEST" ldtt.yaml || { echo "wheel digest != ldtt.yaml build.artifact_digest" >&2; exit 1; }
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
PY="$(command -v python3)"
cat > dist/provenance.predicate.json <<JSON
{
  "buildDefinition": {
    "buildType": "${REPO}/blob/${SOURCE_COMMIT}/ref-connectors/ldtt-ref-mav-observer/scripts/build_release.sh",
    "externalParameters": {
      "source": {"uri": "git+${REPO}", "digest": {"gitCommit": "${SOURCE_COMMIT}"}},
      "path": "ref-connectors/ldtt-ref-mav-observer",
      "command": "scripts/build_release.sh",
      "SOURCE_DATE_EPOCH": "1791244800"
    },
    "internalParameters": {"build_backend": "setuptools==84.0.0 wheel==0.48.0 (pinned in pyproject)", "reproducible": true},
    "resolvedDependencies": [{"uri": "git+${REPO}", "digest": {"gitCommit": "${SOURCE_COMMIT}"}}]
  },
  "runDetails": {
    "builder": {"id": "https://ldtt.example/builders/local-draft-box", "version": {"draft": "phase-2"}},
    "metadata": {"invocationId": "local-${NOW}", "startedOn": "${NOW}", "finishedOn": "${NOW}"},
    "byproducts": [{"name": "note", "content": "$(printf 'Local draft builder; placeholder key; NOT SLSA L2+. CI keyless + GitHub attestation pending workflow scope.' | base64 -w0)"}]
  }
}
JSON
"$COSIGN" sign-blob --yes --key "$KEY" --bundle dist/ldtt-ref-mav-observer.sigstore.json "$WHL" >/dev/null 2>&1
"$COSIGN" attest-blob --yes --key "$KEY" --type slsaprovenance1 \
  --predicate dist/provenance.predicate.json \
  --output-attestation dist/provenance.intoto.jsonl \
  --bundle dist/provenance.intoto.sigstore.json "$WHL" >/dev/null 2>&1
"$COSIGN" verify-blob --key "$PUB" --bundle dist/ldtt-ref-mav-observer.sigstore.json "$WHL"
"$COSIGN" verify-blob-attestation --key "$PUB" --type slsaprovenance1 \
  --bundle dist/provenance.intoto.sigstore.json "$WHL"
echo "signed: $WHL sha256:$DIGEST source_commit=$SOURCE_COMMIT"
