#!/usr/bin/env python3
"""Build and check an append-only Revoke list (Spec §A.2.1, §A.3.6).

  build --base BASE.json --published PUBLISHED.json --extra-revoked EXTRA.json
        --issued-at ISO8601Z --out OUT.json
  check --base BASE.json --published PUBLISHED.json --candidate CANDIDATE.json
  check-time (--list DOC | --doc DOC) --bundle BUNDLE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


FUTURE_LIMIT_S = 300
PAST_LIMIT_S = 3600
ISSUED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def die(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def read_bytes(path: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except FileNotFoundError:
        die(f"not found: {path}")
    except OSError as exc:
        die(f"cannot read {path}: {exc}")


def read_json(path: str, raw: bytes | None = None):
    if raw is None:
        raw = read_bytes(path)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"invalid JSON {path}: {exc}")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def require_object(value, label: str) -> dict:
    if not isinstance(value, dict):
        die(f"{label} must be a JSON object")
    return value


def require_int(value, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        die(f"{label} must be an integer")
    return value


def entry_key(entry: dict) -> tuple[str, str, str]:
    connector_id = entry.get("connector_id")
    version = entry.get("version")
    digest = entry.get("digest")
    if not isinstance(connector_id, str) or not isinstance(version, str) or not isinstance(digest, str):
        die("revoked entry needs string connector_id, version, and digest")
    return (connector_id, version, digest)


def merge_revoked(*groups: object) -> list:
    """Superset of every group. Identical connector_id+version+digest collapses; edits fail."""
    merged: list = []
    seen: dict[tuple[str, str, str], dict] = {}
    for group in groups:
        if not isinstance(group, list):
            die("revoked must be an array")
        for entry in group:
            if not isinstance(entry, dict):
                die("revoked entry must be an object")
            key = entry_key(entry)
            prior = seen.get(key)
            if prior is not None:
                if prior != entry:
                    die(
                        "revoked entry edited for "
                        f"connector_id={key[0]} version={key[1]} digest={key[2]}"
                    )
                continue
            seen[key] = entry
            merged.append(entry)
    return merged


def is_superset(candidate: object, required: object, label: str) -> None:
    if not isinstance(candidate, list) or not isinstance(required, list):
        die(f"{label}: revoked must be an array")
    pool = list(candidate)
    for entry in required:
        try:
            pool.remove(entry)
        except ValueError:
            die(f"candidate.revoked is not a superset of {label} (entry removed or edited)")


def build_list(base_path: str, published_path: str, extra_path: str, issued_at: str) -> dict:
    base_raw = read_bytes(base_path)
    base = require_object(read_json(base_path, base_raw), "base")
    published = require_object(read_json(published_path), "published")
    extra = read_json(extra_path)
    if not isinstance(extra, list):
        die("extra-revoked must be a JSON array")
    if "ldtt_spec" not in published or "issuer" not in published:
        die("published list missing ldtt_spec or issuer")
    published_version = require_int(published.get("list_version"), "published.list_version")
    base_version = require_int(base.get("list_version"), "base.list_version")
    if not isinstance(issued_at, str) or issued_at == "":
        die("issued_at must be a non-empty string")
    revoked = merge_revoked(base.get("revoked", []), published.get("revoked", []), extra)
    return {
        "ldtt_spec": published["ldtt_spec"],
        "issuer": published["issuer"],
        "list_version": published_version + 1,
        "issued_at": issued_at,
        "revoked": revoked,
        "base": {
            "list_version": base_version,
            "sha256": sha256_bytes(base_raw),
        },
    }


def cmd_build(args: argparse.Namespace) -> int:
    doc = build_list(args.base, args.published, args.extra_revoked, args.issued_at)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((json.dumps(doc, indent=2) + "\n").encode("utf-8"))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    base_raw = read_bytes(args.base)
    base = require_object(read_json(args.base, base_raw), "base")
    published = require_object(read_json(args.published), "published")
    candidate = require_object(read_json(args.candidate), "candidate")

    base_version = require_int(base.get("list_version"), "base.list_version")
    published_version = require_int(published.get("list_version"), "published.list_version")
    pointer = candidate.get("base")
    if not isinstance(pointer, dict):
        die("candidate.base must be an object")
    if pointer.get("list_version") != base_version:
        die(
            "candidate.base.list_version "
            f"{pointer.get('list_version')!r} != base list_version {base_version}"
        )
    digest = sha256_bytes(base_raw)
    if pointer.get("sha256") != digest:
        die("candidate.base.sha256 != sha256 of base file bytes")

    is_superset(candidate.get("revoked"), base.get("revoked", []), "base.revoked")
    is_superset(candidate.get("revoked"), published.get("revoked", []), "published.revoked")

    if candidate.get("list_version") != published_version + 1:
        die(
            "candidate.list_version "
            f"{candidate.get('list_version')!r} != published.list_version + 1 ({published_version + 1})"
        )
    if candidate.get("issuer") != published.get("issuer"):
        die("candidate.issuer != published.issuer")
    if candidate.get("ldtt_spec") != published.get("ldtt_spec"):
        die("candidate.ldtt_spec != published.ldtt_spec")
    issued_at = candidate.get("issued_at")
    if not isinstance(issued_at, str) or issued_at == "":
        die("candidate.issued_at must be a non-empty string")
    return 0


def parse_issued_at(value: object) -> int:
    if not isinstance(value, str) or not ISSUED_AT_RE.fullmatch(value):
        die("issued_at must be UTC YYYY-MM-DDTHH:MM:SSZ")
    dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def coerce_unix(value: object) -> int:
    if isinstance(value, bool):
        die("integratedTime must be unix seconds")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"-?\d+", value):
        return int(value)
    die("integratedTime must be unix seconds")
    raise AssertionError("unreachable")


def integrated_time(bundle: dict) -> int | None:
    """First Rekor integrated time, if the bundle carries one.

    Accepted shapes: rekorBundle.Payload.integratedTime, else
    verificationMaterial.tlogEntries[].integratedTime. Unix seconds, int or
    decimal string (protobuf JSON).
    """
    rekor = bundle.get("rekorBundle")
    if isinstance(rekor, dict):
        payload = rekor.get("Payload")
        if isinstance(payload, dict) and "integratedTime" in payload:
            return coerce_unix(payload["integratedTime"])
    material = bundle.get("verificationMaterial")
    if isinstance(material, dict):
        entries = material.get("tlogEntries")
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and "integratedTime" in entry:
                    return coerce_unix(entry["integratedTime"])
    return None


def cmd_check_time(args: argparse.Namespace) -> int:
    docs = [p for p in (args.list_doc, args.doc) if p]
    if len(docs) != 1:
        die("pass exactly one of --list or --doc", code=2)
    doc = require_object(read_json(docs[0]), "doc")
    bundle = require_object(read_json(args.bundle), "bundle")
    issued = parse_issued_at(doc.get("issued_at"))
    integrated = integrated_time(bundle)
    if integrated is None:
        die("no integrated time in bundle")
    delta = issued - integrated
    if delta > FUTURE_LIMIT_S:
        die(f"issued_at is {delta}s after integrated time (limit {FUTURE_LIMIT_S}s)")
    if delta < -PAST_LIMIT_S:
        die(f"issued_at is {-delta}s before integrated time (limit {PAST_LIMIT_S}s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare and check an LDTT revocation list.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build")
    build.add_argument("--base", required=True)
    build.add_argument("--published", required=True)
    build.add_argument("--extra-revoked", required=True)
    build.add_argument("--issued-at", required=True)
    build.add_argument("--out", required=True)
    build.set_defaults(func=cmd_build)

    check = sub.add_parser("check")
    check.add_argument("--base", required=True)
    check.add_argument("--published", required=True)
    check.add_argument("--candidate", required=True)
    check.set_defaults(func=cmd_check)

    timing = sub.add_parser("check-time")
    timing.add_argument("--list", dest="list_doc")
    timing.add_argument("--doc")
    timing.add_argument("--bundle", required=True)
    timing.set_defaults(func=cmd_check_time)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
