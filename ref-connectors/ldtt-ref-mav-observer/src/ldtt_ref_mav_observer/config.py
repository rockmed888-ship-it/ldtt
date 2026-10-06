"""Load ldtt.yaml and validate against LDTT schema (Phase 2 draft)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore


def find_schema(start: Path | None = None) -> Path:
    """Locate schema/ldtt.schema.json relative to this repo or LDTT workspace."""
    here = start or Path(__file__).resolve()
    candidates = [
        here.parents[4] / "schema" / "ldtt.schema.json",  # .../ldtt/schema from src/...
        here.parents[3] / "schema" / "ldtt.schema.json",
        Path("/workspace/ldtt/schema/ldtt.schema.json"),
    ]
    # ref-connectors/ldtt-ref-mav-observer/src/ldtt_ref_mav_observer/config.py
    # parents[0]=pkg, [1]=src, [2]=connector, [3]=ref-connectors, [4]=ldtt
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError("ldtt.schema.json not found")


def load_manifest(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_manifest(doc: dict[str, Any], schema_path: Path | None = None) -> list[str]:
    if jsonschema is None:
        return ["jsonschema not installed"]
    schema_path = schema_path or find_schema()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [e.message for e in validator.iter_errors(doc)]
