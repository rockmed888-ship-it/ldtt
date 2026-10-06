"""C5 append-only JSONL audit log (Phase 2 draft).

Creator lock #3 (Phase 2): ``audit_log.includes`` is the MINIMUM set of event
types the connector must emit, not an exhaustive filter. ``refuse`` / ``deny``
events are evidence-positive and may ALWAYS be written even though they are not
in the schema ``includes`` enum. The writer never drops an event because it is
absent from ``includes``.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Event types that are always writable regardless of ``includes`` (lock #3).
ALWAYS_ALLOWED_EVENTS: frozenset[str] = frozenset({"refuse", "deny"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AuditLog:
    """Append-only JSONL writer. Does not store vehicle telemetry payloads."""

    def __init__(self, path: str, includes: list[str] | None = None) -> None:
        self.path = Path(os.path.expanduser(path))
        # Minimum required set (schema enum). Not a filter.
        self.includes = list(includes or [])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._written: set[str] = set()

    def is_writable(self, event_type: str) -> bool:
        """includes = minimum set; refuse/deny always allowed; others allowed too."""
        return True  # never filter: refuse/deny (ALWAYS_ALLOWED_EVENTS) + includes + extras

    def write(self, event_type: str, **fields: Any) -> None:
        record: dict[str, Any] = {
            "ts": _utc_now(),
            "event": event_type,
            **fields,
        }
        line = json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line)
            self._written.add(event_type)

    def missing_required(self) -> list[str]:
        """Event types in ``includes`` (minimum set) not yet written this process."""
        return [e for e in self.includes if e not in self._written]

    def session(self, action: str, **fields: Any) -> None:
        self.write("session", action=action, **fields)

    def scope_grant(self, scopes: list[str], **fields: Any) -> None:
        self.write("scope_grant", scopes=scopes, **fields)

    def egress_opt_in(self, enabled: bool, **fields: Any) -> None:
        self.write("egress_opt_in", enabled=enabled, **fields)

    def revocation_check(self, outcome: str, **fields: Any) -> None:
        self.write("revocation_check", outcome=outcome, **fields)

    def refuse(self, reason: str, **fields: Any) -> None:
        """TX allowlist / rate refuse. Always writable (lock #3)."""
        self.write("refuse", reason=reason, **fields)

    def deny(self, reason: str, **fields: Any) -> None:
        """Policy deny (e.g. revoked / fail-closed). Always writable (lock #3)."""
        self.write("deny", reason=reason, **fields)
