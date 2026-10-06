"""Phase 2: in-process verify + A1 no fail-open + local placeholder path."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ldtt_ref_mav_observer.cosign_verify import find_cosign, verify_blob
from ldtt_ref_mav_observer.revocation_checker import RevocationChecker

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = ROOT / "placeholders" / "revocations" / "revocations.json"
PUB = ROOT / "placeholders" / "keys" / "ldtt-placeholder.pub"
BUNDLE = ROOT / "placeholders" / "revocations" / "revocations.json.sigstore.json"


def test_placeholder_files_exist():
    assert PLACEHOLDER.is_file()
    assert BUNDLE.is_file()
    assert PUB.is_file()
    data = json.loads(PLACEHOLDER.read_text())
    assert data["revoked"] == []
    assert data["list_version"] >= 1


def test_inprocess_local_key_verify_placeholder():
    """A1: cryptography verifies local-key cosign bundle without shelling to cosign."""
    result = verify_blob(PLACEHOLDER, bundle_path=BUNDLE, key_path=PUB)
    assert result.ok, result.detail
    assert result.mode == "verified_local_key"


def test_cosign_cli_verify_placeholder_when_available():
    cosign = find_cosign()
    if cosign is None:
        pytest.skip("cosign not installed on this host")
    # Force CLI path by using verify via subprocess indirectly: still ok through verify_blob
    result = verify_blob(PLACEHOLDER, bundle_path=BUNDLE, key_path=PUB, cosign_path=cosign)
    assert result.ok, result.detail


def test_a1_missing_verify_no_fail_open():
    """A1: Observe does NOT fail-open; unsigned path never loads list."""
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    body = PLACEHOLDER.read_bytes()
    bundle = BUNDLE.read_bytes()

    def fetch(url: str) -> bytes:
        if url.endswith(".sigstore.json"):
            return bundle
        return body

    c = RevocationChecker(
        list_url=str(PLACEHOLDER),
        connector_id="org.ldtt.ref-mav-observer",
        version="0.1.0",
        digest="sha256:" + ("00" * 32),
        max_staleness_s=86400 * 365,
        fetch_fn=fetch,
        verify_fn=lambda _b, _s: False,
        bundle_url=str(BUNDLE),
    )
    c._last_verify_mode = "cosign_missing"
    outcome = c.check(now=now)
    assert outcome == "unreachable_no_cache"
    assert c.is_fail_closed
    assert c.state.raw is None
