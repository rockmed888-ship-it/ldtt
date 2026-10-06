#!/usr/bin/env python3
"""N3 evidence gate: fail if any E5/E6/E8 evidence was produced with dev-only flags.

Scans ``evidence/`` (excluding ``evidence/superseded-dev-flags/``) for:
  * audit JSONL lines with ``revocation_check.outcome`` in SKIP_OUTCOMES, or ``dev_mode: true``
  * recorded command lines / text containing ``--skip-revoke`` / ``--no-interval-check`` / ``LDTT_DEV=1``
Exit 0 = clean; 1 = evidence relies on skip flags.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ldtt_ref_mav_observer.dev_flags import DEV_ONLY_FLAGS, SKIP_OUTCOMES  # noqa: E402

EXCLUDE_DIRS = {"superseded-dev-flags"}
TEXT_MARKERS = tuple(DEV_ONLY_FLAGS) + ("LDTT_DEV=1",)
# Files that document the gate itself (may name the flags in prose)
DOC_FILES = {"LDTT-Evidence-Checklist-v0.1.3.md", "e6-n3-dev-flag-gate.md"}


def scan(evid: Path) -> list[str]:
    problems: list[str] = []
    for f in sorted(evid.rglob("*")):
        if not f.is_file() or any(p in EXCLUDE_DIRS for p in f.relative_to(evid).parts):
            continue
        if f.name in DOC_FILES:
            continue
        rel = f.relative_to(evid)
        text = f.read_text(errors="replace")
        if f.suffix == ".jsonl":
            for i, line in enumerate(text.splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("event") == "revocation_check" and rec.get("outcome") in SKIP_OUTCOMES:
                    problems.append(f"{rel}:{i}: revocation_check outcome={rec['outcome']}")
                if rec.get("dev_mode") is True:
                    problems.append(f"{rel}:{i}: dev_mode=true")
        # pytest outputs name the tests (test_*skip*), which is fine; only flag CLI invocations
        if f.name.endswith("-pytest-output.txt"):
            continue
        for m in TEXT_MARKERS:
            if m in text:
                problems.append(f"{rel}: contains '{m}'")
    return problems


def main(argv: list[str] | None = None) -> int:
    evid = Path(argv[0]) if argv else ROOT / "evidence"
    problems = scan(evid)
    if problems:
        print("EVIDENCE USES DEV-ONLY FLAGS (N3 FAIL):")
        for p in problems:
            print(" -", p)
        return 1
    print(f"N3 OK: no evidence under {evid} relies on {', '.join(DEV_ONLY_FLAGS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
