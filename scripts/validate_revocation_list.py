#!/usr/bin/env python3
"""W5 shape check for an LDTT revocation list. No separate schema file.

  python3 scripts/validate_revocation_list.py --require-base PATH
  python3 scripts/validate_revocation_list.py --forbid-base PATH

--require-base: Revoke lists must carry base {list_version, sha256}.
--forbid-base: Issuer lists must omit base.
Exit 0 on success, exit 1 with a reason on stderr.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


UTC_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def die(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check_utc(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.endswith("Z") or not UTC_Z.fullmatch(value):
        die(f"{label} must be a UTC string ending with Z")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        die(f"{label} is not a valid UTC timestamp")


def check_entry(entry: object, index: int) -> None:
    if not isinstance(entry, dict):
        die(f"revoked[{index}] must be an object")
    connector_id = entry.get("connector_id")
    version = entry.get("version")
    digest = entry.get("digest")
    reason = entry.get("reason")
    if not isinstance(connector_id, str):
        die(f"revoked[{index}].connector_id must be a string")
    if not isinstance(version, str):
        die(f"revoked[{index}].version must be a string")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        die(f"revoked[{index}].digest must be a string starting with sha256:")
    check_utc(entry.get("revoked_at"), f"revoked[{index}].revoked_at")
    if not isinstance(reason, str) or reason == "":
        die(f"revoked[{index}].reason must be a non-empty string")


def check_base(base: object) -> None:
    if not isinstance(base, dict):
        die("base must be an object")
    if set(base) != {"list_version", "sha256"}:
        die('base must be {"list_version": int, "sha256": 64 lowercase hex}')
    if not is_int(base["list_version"]) or base["list_version"] < 1:
        die("base.list_version must be an integer >= 1")
    sha = base["sha256"]
    if not isinstance(sha, str) or not SHA256_HEX.fullmatch(sha):
        die("base.sha256 must be 64 lowercase hex")


def validate(doc: object, require_base: bool) -> None:
    if not isinstance(doc, dict):
        die("revocation list must be a JSON object")
    if not isinstance(doc.get("ldtt_spec"), str):
        die("ldtt_spec must be a string")
    if not isinstance(doc.get("issuer"), str):
        die("issuer must be a string")
    version = doc.get("list_version")
    if not is_int(version) or version < 1:
        die("list_version must be an integer >= 1")
    check_utc(doc.get("issued_at"), "issued_at")
    revoked = doc.get("revoked")
    if not isinstance(revoked, list):
        die("revoked must be an array")
    for index, entry in enumerate(revoked):
        check_entry(entry, index)
    if require_base:
        if "base" not in doc:
            die("base is required")
        check_base(doc["base"])
    elif "base" in doc:
        die("base must be absent")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an LDTT revocation list shape.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--require-base", metavar="PATH")
    mode.add_argument("--forbid-base", metavar="PATH")
    args = parser.parse_args(argv)
    path = args.require_base or args.forbid_base
    try:
        raw = Path(path).read_bytes()
    except FileNotFoundError:
        die(f"not found: {path}")
    except OSError as exc:
        die(f"cannot read {path}: {exc}")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"invalid JSON: {exc}")
    validate(doc, require_base=args.require_base is not None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
