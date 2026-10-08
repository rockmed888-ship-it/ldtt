"""Fail-closed check for a Listing Developers Trust Tool draft.

A listing that claims a real stamp, a model key leaving the host, or a host
company that enforces LDTT is rejected. Drafts must say so.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


HUMAN_GATES = ("send", "post", "pay")
SECRET_KEYS = re.compile(r"(api[_-]?key|secret|bearer|token|password|authorization)", re.I)
POLICY_FIELDS = {"customer_receives_api_key", "model_key_leaves_host"}
SECRET_VALUE = re.compile(r"\b(sk-|pk_live|xai-|ghp_|gho_|Bearer\s+[A-Za-z0-9._\-]{8,})")


def die(message: str) -> None:
    print(f"mcp-listing: {message}", file=sys.stderr)
    raise SystemExit(1)


def walk_secrets(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in POLICY_FIELDS and SECRET_KEYS.search(str(key)):
                die(f"secret-like field {path}.{key}")
            walk_secrets(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            walk_secrets(item, f"{path}[{index}]")
    elif isinstance(value, str) and SECRET_VALUE.search(value):
        die(f"secret-like value at {path}")


def validate(doc: dict[str, Any]) -> None:
    if doc.get("ldtt_line") != "listing-developers-trust-tool":
        die("ldtt_line must be listing-developers-trust-tool")
    if doc.get("ldtt_spec") != "mcp-0.1-draft":
        die("ldtt_spec must be mcp-0.1-draft")
    if doc.get("status") != "draft":
        die("status must be draft until the Issuer signs a later revision")
    if doc.get("real_stamp") is not False:
        die("real_stamp must be false")
    if not isinstance(doc.get("connector_id"), str) or not doc["connector_id"].startswith("org.ldtt."):
        die("connector_id must start with org.ldtt.")
    transport = doc.get("transport")
    if transport not in ("mcp", "host-proof"):
        die("transport must be mcp or host-proof")
    controls = doc.get("controls")
    if not isinstance(controls, dict):
        die("controls object is required")
    if controls.get("model_key_leaves_host") is not False:
        die("model_key_leaves_host must be false")
    if controls.get("customer_receives_api_key") is not False:
        die("customer_receives_api_key must be false")
    if controls.get("undeclared_egress") != "deny":
        die("undeclared_egress must be deny")
    gates = controls.get("human_gates")
    if not isinstance(gates, list) or any(gate not in gates for gate in HUMAN_GATES):
        die("human_gates must include send, post, and pay")
    if doc.get("host_enforcement") != "none":
        die("host_enforcement must be none until a host ships an LDTT check")
    tools = doc.get("tools_declared")
    evidence = doc.get("tools_evidence")
    if transport == "mcp":
        if not isinstance(tools, list) or not tools:
            die("mcp listing needs a non-empty tools_declared")
        if evidence not in ("owner-declaration", "tools-list"):
            die("tools_evidence must be owner-declaration or tools-list")
        if evidence == "tools-list" and doc.get("tools_list_sha256") in (None, ""):
            die("tools-list evidence needs tools_list_sha256")
    elif tools not in (None, []) or evidence not in (None, "not-an-mcp-server"):
        die("host-proof must not invent an MCP tool list")
    notes = doc.get("known_limitations")
    if not isinstance(notes, list) or not any("not a real stamp" in str(note).lower() for note in notes):
        die("known_limitations must say this is not a real stamp")
    walk_secrets(doc, "$")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an LDTT MCP listing draft")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    for raw in args.paths:
        path = Path(raw)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            die(f"{path}: {exc}")
        if not isinstance(doc, dict):
            die(f"{path}: not an object")
        validate(doc)
        print(f"ok {path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
