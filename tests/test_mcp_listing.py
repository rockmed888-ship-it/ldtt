"""Listing Developers Trust Tool drafts stay honest."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_mcp_listing.py"
LISTINGS = ROOT / "listings"


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_owner_listings_pass():
    paths = sorted(LISTINGS.glob("*.json"))
    assert [path.name for path in paths] == [
        "org.ldtt.brain-connector.json",
        "org.ldtt.brand-agents-dd.json",
        "org.ldtt.brand-agents.json",
        "org.ldtt.dent-coins.json",
    ]
    result = run([str(path) for path in paths])
    assert result.returncode == 0, result.stderr


def test_rejects_real_stamp_and_key_claim(tmp_path: Path):
    doc = json.loads((LISTINGS / "org.ldtt.brain-connector.json").read_text(encoding="utf-8"))
    doc["real_stamp"] = True
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert run([str(path)]).returncode == 1

    doc["real_stamp"] = False
    doc["controls"]["customer_receives_api_key"] = True
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert run([str(path)]).returncode == 1

    doc["controls"]["customer_receives_api_key"] = False
    doc["host_enforcement"] = "google"
    path.write_text(json.dumps(doc), encoding="utf-8")
    refused = run([str(path)])
    assert refused.returncode == 1
    assert "host_enforcement" in refused.stderr
