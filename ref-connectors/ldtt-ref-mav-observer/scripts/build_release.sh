#!/usr/bin/env bash
# E3 / C3: reproducible release wheel for ldtt-ref-mav-observer (Phase 2 draft).
# Same source tree + pinned build backend + SOURCE_DATE_EPOCH => same sha256 (local == CI).
set -euo pipefail
cd "$(dirname "$0")/.."
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1791244800}"   # 2026-10-06T00:00:00Z (pinned)
export PYTHONHASHSEED=0
PY="${PYTHON:-python3}"
[[ -x .venv/bin/python && -z "${PYTHON:-}" ]] && PY=.venv/bin/python
rm -rf build dist/*.whl dist/*.tar.gz
find src -name __pycache__ -prune -exec rm -rf {} +
"$PY" -m build --wheel --outdir dist . >/dev/null 2>&1
rm -rf build
WHL=$(ls dist/ldtt_ref_mav_observer-*-py3-none-any.whl)
DIGEST=$(sha256sum "$WHL" | cut -d' ' -f1)
echo "$DIGEST  $(basename "$WHL")" > dist/SHA256SUMS
echo "artifact: $WHL"
echo "artifact_digest: sha256:$DIGEST"
