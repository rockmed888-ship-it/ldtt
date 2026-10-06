"""C4 revocation checker — signed lists only (Phase 2 draft, Corrector A1 / A1-r).

Never load an unsigned revocation list. Missing/failed signature verification
is treated like list-unreachable: keep the last verified signed list until
max_staleness_s, then fail closed. Rollback (lower list_version) fail-closes.

Disk cache (A1-r): save_cache stores original body bytes + .sigstore.json;
load_cache re-runs verify_fn (ignore on fail) and applies list_version rollback.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
from urllib.parse import urlparse


class RevocationError(RuntimeError):
    """Fail-closed revocation / staleness / rollback condition."""


def _parse_issued_at(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _age_seconds(issued_at: str, now: Optional[datetime] = None) -> float:
    now = now or datetime.now(timezone.utc)
    return (now - _parse_issued_at(issued_at)).total_seconds()


FetchFn = Callable[[str], bytes]
VerifyFn = Callable[[bytes, Optional[bytes]], bool]


def default_fetch(url: str, timeout: float = 10.0) -> bytes:
    """Fetch HTTPS URL, file:// URL, or plain filesystem path."""
    parsed = urlparse(url)
    if parsed.scheme in ("", "file") or url.startswith("./") or url.startswith("../") or url.startswith("/"):
        path = Path(parsed.path if parsed.scheme == "file" else url)
        return path.read_bytes()
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 — URL from manifest/override
        return resp.read()


def stub_verify(_body: bytes, _sig_bundle: Optional[bytes] = None) -> bool:
    """Placeholder for unit tests that inject verify_fn."""
    return True


@dataclass
class RevocationState:
    list_version: int = -1
    issued_at: Optional[str] = None
    raw: Optional[dict[str, Any]] = None
    revoked: bool = False
    fail_closed: bool = False
    last_outcome: str = "uninitialized"
    cosign_mode: str = "uninitialized"
    # True only after a signature-verified list was accepted this process
    has_verified_list: bool = False


@dataclass
class RevocationChecker:
    """Checks signed revocations.json with staleness and rollback fail-closed."""

    list_url: str
    connector_id: str
    version: str
    digest: str
    max_staleness_s: int
    fetch_fn: FetchFn = default_fetch
    verify_fn: VerifyFn = stub_verify
    cache_path: Optional[Path] = None
    bundle_url: Optional[str] = None  # sibling .sigstore.json or override
    state: RevocationState = field(default_factory=RevocationState)
    # Original verified blob + bundle for cache (exact bytes for re-verify)
    _cached_body: Optional[bytes] = field(default=None, init=False, repr=False)
    _cached_bundle: Optional[bytes] = field(default=None, init=False, repr=False)

    def _bundle_cache_path(self) -> Optional[Path]:
        if not self.cache_path:
            return None
        return Path(str(self.cache_path) + ".sigstore.json")

    def load_cache(self) -> None:
        """Load disk cache only after re-verify; ignore on verify/rollback failure (A1-r)."""
        if not self.cache_path or not self.cache_path.exists():
            return
        body = self.cache_path.read_bytes()
        bundle_path = self._bundle_cache_path()
        bundle: Optional[bytes] = None
        if bundle_path is not None and bundle_path.exists():
            bundle = bundle_path.read_bytes()
        if not self.verify_fn(body, bundle):
            # Tampered / unsigned cache — ignore (never load unsigned list)
            return
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        try:
            # A1-r: apply list_version rollback check (same as live fetch)
            self._apply_list(data, from_cache=False)
        except RevocationError:
            return
        self._cached_body = body
        self._cached_bundle = bundle
        self.state.has_verified_list = True
        self.state.cosign_mode = "cache_last_verified"

    def save_cache(self) -> None:
        """Persist original verified body bytes + sibling .sigstore.json (A1-r).

        Do NOT re-json.dumps the parsed dict — that changes bytes and breaks
        the signature over the original blob.
        """
        if not self.cache_path or self._cached_body is None:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_bytes(self._cached_body)
        bundle_path = self._bundle_cache_path()
        if bundle_path is not None and self._cached_bundle is not None:
            bundle_path.write_bytes(self._cached_bundle)

    def _fetch_bundle(self) -> Optional[bytes]:
        if not self.bundle_url:
            if self.list_url.endswith(".json"):
                candidate = self.list_url + ".sigstore.json"
            else:
                candidate = self.list_url.rstrip("/") + ".sigstore.json"
            self.bundle_url = candidate
        try:
            return self.fetch_fn(self.bundle_url)
        except (urllib.error.URLError, TimeoutError, OSError, FileNotFoundError):
            return None

    def check(self, now: Optional[datetime] = None) -> str:
        """Fetch/update list and evaluate. Returns outcome string for audit.

        Outcomes: ok | revoked | stale_fail_closed | rollback_rejected |
                  unreachable_using_cache | unreachable_no_cache |
                  signature_verify_failed (via unreachable path)
        """
        now = now or datetime.now(timezone.utc)
        try:
            body = self.fetch_fn(self.list_url)
        except (urllib.error.URLError, TimeoutError, OSError, FileNotFoundError) as exc:
            return self._on_unreachable(now, str(exc))

        bundle = self._fetch_bundle()
        verified = self.verify_fn(body, bundle)
        if not verified:
            # A1: never load unsigned / unverified list contents.
            # Treat as unreachable — keep last verified list or fail closed.
            mode = getattr(self, "_last_verify_mode", None) or "verify_failed"
            self.state.cosign_mode = mode
            return self._on_unreachable(now, f"signature_unverified:{mode}")

        self.state.cosign_mode = getattr(self, "_last_verify_mode", None) or "verified"
        data = json.loads(body.decode("utf-8"))
        try:
            self._apply_list(data, from_cache=False, now=now)
        except RevocationError as exc:
            if "rollback" in str(exc).lower():
                # A1 / Spec §5.2: reject rollback and fail closed (warn + halt)
                self.state.fail_closed = True
                self.state.last_outcome = "rollback_rejected"
                return self.state.last_outcome
            raise

        self.state.has_verified_list = True
        self._cached_body = body
        self._cached_bundle = bundle
        self.save_cache()
        return self._evaluate(now)

    def _on_unreachable(self, now: datetime, reason: str) -> str:
        if self.state.raw is None or self.state.issued_at is None or not self.state.has_verified_list:
            # No last verified list → same as unavailable list → fail closed
            self.state.fail_closed = True
            self.state.last_outcome = "unreachable_no_cache"
            return self.state.last_outcome
        age = _age_seconds(self.state.issued_at, now)
        if age > self.max_staleness_s:
            self.state.fail_closed = True
            self.state.last_outcome = "stale_fail_closed"
            return self.state.last_outcome
        self._evaluate(now)
        if self.state.revoked:
            self.state.last_outcome = "revoked"
            return self.state.last_outcome
        self.state.last_outcome = "unreachable_using_cache"
        return self.state.last_outcome

    def _apply_list(
        self,
        data: Mapping[str, Any],
        *,
        from_cache: bool,
        now: Optional[datetime] = None,
    ) -> None:
        list_version = int(data["list_version"])
        issued_at = str(data["issued_at"])
        if not from_cache and self.state.list_version >= 0 and list_version < self.state.list_version:
            raise RevocationError(
                f"rollback rejected: list_version {list_version} < {self.state.list_version}"
            )
        self.state.list_version = list_version
        self.state.issued_at = issued_at
        self.state.raw = dict(data)
        if now is not None:
            age = _age_seconds(issued_at, now)
            if age > self.max_staleness_s:
                self.state.fail_closed = True
                self.state.last_outcome = "stale_fail_closed"

    def _evaluate(self, now: datetime) -> str:
        assert self.state.raw is not None and self.state.issued_at is not None
        age = _age_seconds(self.state.issued_at, now)
        if age > self.max_staleness_s:
            self.state.fail_closed = True
            self.state.last_outcome = "stale_fail_closed"
            return self.state.last_outcome

        for entry in self.state.raw.get("revoked", []):
            if entry.get("connector_id") != self.connector_id:
                continue
            ver = entry.get("version")
            dig = entry.get("digest")
            ver_match = ver == "*" or ver == self.version
            dig_match = dig is None or dig == self.digest
            if ver_match and dig_match:
                self.state.revoked = True
                self.state.fail_closed = True
                self.state.last_outcome = "revoked"
                return self.state.last_outcome

        self.state.revoked = False
        self.state.fail_closed = False
        self.state.last_outcome = "ok"
        return self.state.last_outcome

    @property
    def is_fail_closed(self) -> bool:
        return self.state.fail_closed or self.state.revoked
