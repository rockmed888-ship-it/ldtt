"""Unit tests: C4 revocation — A1/A1-r signed-only, cache re-verify, staleness, rollback (Phase 2)."""

import json
from datetime import datetime, timezone
from pathlib import Path

from ldtt_ref_mav_observer.revocation_checker import RevocationChecker


CONNECTOR = "org.ldtt.ref-mav-observer"
VERSION = "0.1.0"
DIGEST = "sha256:" + ("ab" * 32)


def _list(version: int, issued_at: str, revoked=None):
    return {
        "ldtt_spec": "0.1.4",
        "issuer": "LDTT",
        "list_version": version,
        "issued_at": issued_at,
        "revoked": revoked or [],
    }


def test_ok_empty_list():
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    body = json.dumps(_list(1, "2026-10-06T11:00:00Z")).encode()
    c = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=lambda url: body,
    )
    assert c.check(now=now) == "ok"
    assert not c.is_fail_closed
    assert c.state.has_verified_list


def test_revoked():
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    revoked = [
        {
            "connector_id": CONNECTOR,
            "version": VERSION,
            "digest": DIGEST,
            "revoked_at": "2026-10-05T18:00:00Z",
            "reason": "test",
        }
    ]
    body = json.dumps(_list(2, "2026-10-06T11:00:00Z", revoked)).encode()
    c = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=lambda url: body,
    )
    assert c.check(now=now) == "revoked"
    assert c.is_fail_closed


def test_unreachable_within_staleness_uses_cache():
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    good = json.dumps(_list(3, "2026-10-06T10:00:00Z")).encode()
    c = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=lambda url: good,
    )
    assert c.check(now=now) == "ok"

    def boom(_url):
        raise TimeoutError("down")

    c.fetch_fn = boom
    assert c.check(now=now) == "unreachable_using_cache"
    assert not c.is_fail_closed


def test_beyond_staleness_fail_closed():
    issued = "2026-10-01T00:00:00Z"
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)  # > 86400s later
    good = json.dumps(_list(1, issued)).encode()
    c = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=lambda url: good,
    )
    assert c.check(now=now) == "stale_fail_closed"
    assert c.is_fail_closed


def test_rollback_rejected_fail_closed():
    """A1 / Spec §5.2: lower list_version → reject + fail closed (do not keep running as ok)."""
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    v7 = json.dumps(_list(7, "2026-10-06T11:00:00Z")).encode()
    v6 = json.dumps(_list(6, "2026-10-06T12:00:00Z")).encode()
    c = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=lambda url: v7,
    )
    assert c.check(now=now) == "ok"
    c.fetch_fn = lambda url: v6
    assert c.check(now=now) == "rollback_rejected"
    assert c.state.list_version == 7  # kept previous
    assert c.is_fail_closed  # A1: fail closed — refuse sessions


def test_wildcard_version_revokes():
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    revoked = [{"connector_id": CONNECTOR, "version": "*", "digest": DIGEST, "revoked_at": "2026-10-05T18:00:00Z", "reason": "x"}]
    body = json.dumps(_list(1, "2026-10-06T11:00:00Z", revoked)).encode()
    c = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=lambda url: body,
    )
    assert c.check(now=now) == "revoked"


def test_unverified_never_loads_list_no_cache_fail_closed():
    """A1: verify failure with no last verified list → unreachable_no_cache / fail closed."""
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    body = json.dumps(_list(1, "2026-10-06T11:00:00Z")).encode()
    c = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=lambda url: body,
        verify_fn=lambda _b, _s: False,
    )
    c._last_verify_mode = "cosign_missing"
    assert c.check(now=now) == "unreachable_no_cache"
    assert c.is_fail_closed
    assert c.state.raw is None  # never loaded unsigned body


def test_unverified_keeps_last_verified_within_staleness():
    """A1: cosign-missing / verify-failed like unreachable — keep last verified list."""
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    good = json.dumps(_list(5, "2026-10-06T10:00:00Z")).encode()
    c = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=lambda url: good,
    )
    assert c.check(now=now) == "ok"
    assert c.state.list_version == 5

    # Attacker / unsigned newer body must not be applied
    evil = json.dumps(_list(99, "2026-10-06T11:30:00Z", [
        {"connector_id": CONNECTOR, "version": "*", "digest": DIGEST, "revoked_at": "2026-10-06T11:00:00Z", "reason": "evil"}
    ])).encode()
    c.fetch_fn = lambda url: evil
    c.verify_fn = lambda _b, _s: False
    c._last_verify_mode = "cosign_missing"
    assert c.check(now=now) == "unreachable_using_cache"
    assert c.state.list_version == 5  # unsigned evil list NOT loaded
    assert not c.state.revoked
    assert not c.is_fail_closed


def test_save_cache_preserves_original_body_and_bundle(tmp_path):
    """A1-r: save_cache writes original body bytes (not re-dumps) + .sigstore.json."""
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    # Compact JSON — json.dumps(indent=2) would change these bytes
    body = (
        b'{"ldtt_spec":"0.1.4","issuer":"LDTT","list_version":1,'
        b'"issued_at":"2026-10-06T11:00:00Z","revoked":[]}'
    )
    bundle = b'{"payload":"fake-sigstore-bundle"}'
    cache = tmp_path / "org.ldtt.ref-mav-observer.revocations.json"

    def fetch(url: str) -> bytes:
        if url.endswith(".sigstore.json"):
            return bundle
        return body

    c = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=fetch,
        cache_path=cache,
        bundle_url="https://example.test/revocations.json.sigstore.json",
    )
    assert c.check(now=now) == "ok"
    assert cache.read_bytes() == body
    assert Path(str(cache) + ".sigstore.json").read_bytes() == bundle


def test_tampered_cache_ignored_unreachable_no_cache(tmp_path):
    """A1-r: tampered cache fails verify → ignored → unreachable_no_cache / fail closed."""
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    cache = tmp_path / "org.ldtt.ref-mav-observer.revocations.json"
    # Attacker-edited issued_at / list on disk
    tampered = json.dumps(_list(1, "2099-01-01T00:00:00Z")).encode()
    cache.write_bytes(tampered)
    Path(str(cache) + ".sigstore.json").write_bytes(b'{"bundle":"not-matching"}')

    def boom(_url: str) -> bytes:
        raise TimeoutError("list unreachable")

    c = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=boom,
        verify_fn=lambda _b, _s: False,  # re-verify fails on tamper
        cache_path=cache,
    )
    c.load_cache()
    assert not c.state.has_verified_list
    assert c.state.raw is None
    assert c.check(now=now) == "unreachable_no_cache"
    assert c.is_fail_closed


def test_load_cache_reverify_ok_then_unreachable_uses_cache(tmp_path):
    """A1-r: verified cache loads; unreachable fetch uses it within staleness."""
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    body = json.dumps(_list(4, "2026-10-06T10:00:00Z"), separators=(",", ":")).encode()
    bundle = b'{"ok":true}'
    cache = tmp_path / "c.revocations.json"

    def fetch(url: str) -> bytes:
        if url.endswith(".sigstore.json"):
            return bundle
        return body

    c1 = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=fetch,
        cache_path=cache,
        bundle_url="https://example.test/revocations.json.sigstore.json",
    )
    assert c1.check(now=now) == "ok"

    def boom(_url: str) -> bytes:
        raise TimeoutError("down")

    c2 = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=boom,
        verify_fn=lambda b, s: b == body and s == bundle,
        cache_path=cache,
    )
    c2.load_cache()
    assert c2.state.has_verified_list
    assert c2.state.list_version == 4
    assert c2.check(now=now) == "unreachable_using_cache"
    assert not c2.is_fail_closed


def test_load_cache_rollback_ignored(tmp_path):
    """A1-r: cache with lower list_version than current state is ignored."""
    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    v7 = json.dumps(_list(7, "2026-10-06T11:00:00Z")).encode()
    v6 = json.dumps(_list(6, "2026-10-06T10:00:00Z")).encode()
    cache = tmp_path / "c.revocations.json"

    c = RevocationChecker(
        list_url="https://example.test/revocations.json",
        connector_id=CONNECTOR,
        version=VERSION,
        digest=DIGEST,
        max_staleness_s=86400,
        fetch_fn=lambda url: v7,
        cache_path=cache,
    )
    assert c.check(now=now) == "ok"
    assert c.state.list_version == 7

    # Simulate older on-disk cache replacing the saved v7 blob
    cache.write_bytes(v6)
    Path(str(cache) + ".sigstore.json").write_bytes(b'{"b":1}')

    # Reloading older cache must not roll back in-memory state
    c.load_cache()
    assert c.state.list_version == 7
