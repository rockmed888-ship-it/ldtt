"""N3 (Corrector): dev-only gate for revocation-weakening CLI flags (Phase 2 draft).

``--skip-revoke`` and ``--no-interval-check`` weaken C4. They are accepted ONLY when
the operator sets the environment variable ``LDTT_DEV=1`` (exact value). Otherwise the
connector refuses to start (exit 2) and writes an audit ``refuse`` event.

When the gate is open and a flag is used, the connector:
  * prints a WARN to stderr,
  * marks ``session start`` with ``dev_mode: true`` / ``evidence_eligible: false``,
  * audit-logs ``revocation_check`` with ``outcome: "skipped_dev"`` (``--skip-revoke``)
    and/or ``outcome: "interval_skipped_dev"`` (``--no-interval-check`` or implied by
    ``--skip-revoke``).

Why an env var (not a separate build): one wheel = one digest (C3). Stripping flags at
build time would need two artifacts with different digests; an env gate keeps the single
signed artifact while making the weak path explicit, opt-in, and always audited.
Release CI never sets ``LDTT_DEV``; ``scripts/check_evidence_no_dev_flags.py`` fails CI if
any evidence file was produced with these flags.
"""

from __future__ import annotations

import os
from typing import Mapping, Optional

DEV_ENV_VAR = "LDTT_DEV"
DEV_ENV_VALUE = "1"
DEV_ONLY_FLAGS: tuple[str, ...] = ("--skip-revoke", "--no-interval-check")

# Audit outcomes that mark a run as NOT evidence-eligible (E6/E5/E8 must not contain these).
SKIP_OUTCOMES: frozenset[str] = frozenset({"skipped_dev", "interval_skipped_dev"})


def dev_mode_enabled(env: Optional[Mapping[str, str]] = None) -> bool:
    env = os.environ if env is None else env
    return env.get(DEV_ENV_VAR) == DEV_ENV_VALUE


def used_dev_flags(*, skip_revoke: bool, no_interval_check: bool) -> list[str]:
    used = []
    if skip_revoke:
        used.append("--skip-revoke")
    if no_interval_check:
        used.append("--no-interval-check")
    return used
