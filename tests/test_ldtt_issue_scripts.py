"""CLI tests for path guard, revoke prepare, and revocation-list shape."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / "scripts" / "ldtt_path_guard.py"
PREPARE = REPO / "scripts" / "ldtt_revoke_prepare.py"
VALIDATE = REPO / "scripts" / "validate_revocation_list.py"
ISSUED = "2026-10-08T00:00:00Z"
ISSUED_UNIX = int(datetime(2026, 10, 8, tzinfo=timezone.utc).timestamp())
HEX64 = "ab" * 32


def run(script: Path, args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd or REPO,
        capture_output=True,
        text=True,
    )


def write_json(path: Path, doc) -> None:
    path.write_bytes((json.dumps(doc, indent=2) + "\n").encode("utf-8"))


def entry(connector_id: str, reason: str) -> dict:
    return {
        "connector_id": connector_id,
        "version": "1.0.0",
        "digest": f"sha256:{connector_id}",
        "revoked_at": "2026-10-01T00:00:00Z",
        "reason": reason,
    }


def test_path_guard_rejects_escape_absolute_and_outside(tmp_path: Path) -> None:
    stamps = tmp_path / "stamps"
    stamps.mkdir()
    (stamps / "ok.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "outside.json").write_text("{}\n", encoding="utf-8")

    absolute = run(
        GUARD,
        ["--root", "stamps", "--path", str(stamps / "ok.json"), "--must-exist"],
        cwd=tmp_path,
    )
    assert absolute.returncode == 2
    assert "absolute" in absolute.stderr
    assert absolute.stdout == ""

    posix_absolute = run(
        GUARD,
        ["--root", "stamps", "--path", "/etc/passwd", "--must-exist"],
        cwd=tmp_path,
    )
    assert posix_absolute.returncode == 2
    assert "absolute" in posix_absolute.stderr

    escaped = run(
        GUARD,
        ["--root", "stamps", "--path", "stamps/../../outside.json", "--must-exist"],
        cwd=tmp_path,
    )
    assert escaped.returncode == 2
    assert ".." in escaped.stderr

    leaves_and_returns = run(
        GUARD,
        ["--root", "stamps", "--path", "stamps/../stamps/ok.json", "--must-exist"],
        cwd=tmp_path,
    )
    assert leaves_and_returns.returncode == 2
    assert ".." in leaves_and_returns.stderr

    outside = run(
        GUARD,
        ["--root", "stamps", "--path", "trust/trust-root.json", "--must-exist"],
        cwd=tmp_path,
    )
    assert outside.returncode == 2
    assert "outside" in outside.stderr


def test_path_guard_must_exist_and_inner_dotdot(tmp_path: Path) -> None:
    nested = tmp_path / "stamps" / "nested"
    nested.mkdir(parents=True)
    (tmp_path / "stamps" / "ok.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "stamps" / "ok.json.sigstore.json").write_text("{}\n", encoding="utf-8")

    missing = run(
        GUARD,
        ["--root", "stamps", "--path", "stamps/missing.json", "--must-exist"],
        cwd=tmp_path,
    )
    assert missing.returncode == 2
    assert "does not exist" in missing.stderr

    ok = run(
        GUARD,
        ["--root", "stamps", "--path", "stamps/nested/../ok.json", "--must-exist"],
        cwd=tmp_path,
    )
    assert ok.returncode == 0, ok.stderr
    assert ok.stdout.splitlines() == ["stamps/ok.json"]

    bundle = run(
        GUARD,
        ["--root", "stamps", "--path", "stamps/ok.json.sigstore.json", "--must-exist"],
        cwd=tmp_path,
    )
    assert bundle.returncode == 0, bundle.stderr
    assert bundle.stdout.splitlines() == ["stamps/ok.json.sigstore.json"]


def test_path_guard_symlink_escape(tmp_path: Path) -> None:
    stamps = tmp_path / "stamps"
    stamps.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    inside = stamps / "inside.json"
    inside.write_text("{}\n", encoding="utf-8")
    escaped = stamps / "escaped.json"
    stayed = stamps / "stayed.json"
    try:
        escaped.symlink_to(outside)
        stayed.symlink_to(inside)
    except OSError as exc:
        pytest.fail(f"symlink could not be created: {exc}")

    bad = run(
        GUARD,
        ["--root", "stamps", "--path", "stamps/escaped.json", "--must-exist"],
        cwd=tmp_path,
    )
    assert bad.returncode == 2
    assert "symlink" in bad.stderr

    good = run(
        GUARD,
        ["--root", "stamps", "--path", "stamps/stayed.json", "--must-exist"],
        cwd=tmp_path,
    )
    assert good.returncode == 0, good.stderr
    assert good.stdout.splitlines() == ["stamps/inside.json"]


def test_path_guard_repo_stamp_and_trust_root() -> None:
    stamp = run(
        GUARD,
        [
            "--root",
            "stamps",
            "--path",
            "stamps/org.ldtt.ref-mav-observer/0.1.0.json",
            "--must-exist",
        ],
    )
    assert stamp.returncode == 0, stamp.stderr
    assert stamp.stdout.splitlines() == ["stamps/org.ldtt.ref-mav-observer/0.1.0.json"]

    trust = run(GUARD, ["--root", "trust", "--path", "trust/trust-root.json", "--must-exist"])
    assert trust.returncode == 0, trust.stderr
    assert trust.stdout.splitlines() == ["trust/trust-root.json"]

    unsigned = run(
        GUARD,
        ["--root", "trust", "--path", "trust/trust-root.json.sigstore.json", "--must-exist"],
    )
    assert unsigned.returncode == 2
    assert "does not exist" in unsigned.stderr


def test_build_superset_version_and_original_bytes(tmp_path: Path) -> None:
    base_entry = entry("base-conn", "from-base")
    published_entry = entry("pub-conn", "from-published")
    extra_entry = entry("extra-conn", "from-extra")
    # Valid JSON, but not a re-serialization: CRLF and trailing spaces must be hashed as stored.
    base_raw = (
        '{\r\n'
        '  "ldtt_spec": "0.9.9",\r\n'
        '  "issuer": "OTHER",\r\n'
        '  "list_version": 2,\r\n'
        '  "issued_at": "2026-01-01T00:00:00Z",\r\n'
        '  "revoked": ['
        + json.dumps(base_entry)
        + "]   \r\n"
        + "}\r\n"
    ).encode("utf-8")
    assert hashlib.sha256(base_raw).hexdigest() != hashlib.sha256(
        json.dumps(json.loads(base_raw)).encode("utf-8")
    ).hexdigest()
    base_path = tmp_path / "base.json"
    base_path.write_bytes(base_raw)
    published = {
        "ldtt_spec": "0.1.4",
        "issuer": "LDTT",
        "list_version": 4,
        "issued_at": "2026-10-07T00:00:00Z",
        "revoked": [base_entry, published_entry],
    }
    published_path = tmp_path / "published.json"
    write_json(published_path, published)
    extra_path = tmp_path / "extra.json"
    write_json(extra_path, [extra_entry, base_entry])
    out_path = tmp_path / "next.json"

    built = run(
        PREPARE,
        [
            "build",
            "--base",
            str(base_path),
            "--published",
            str(published_path),
            "--extra-revoked",
            str(extra_path),
            "--issued-at",
            ISSUED,
            "--out",
            str(out_path),
        ],
    )
    assert built.returncode == 0, built.stderr
    text = out_path.read_bytes()
    assert text.endswith(b"\n")
    assert b"\r\n" not in text
    doc = json.loads(text)
    assert doc["ldtt_spec"] == "0.1.4"
    assert doc["issuer"] == "LDTT"
    assert doc["list_version"] == 5
    assert doc["issued_at"] == ISSUED
    assert doc["revoked"] == [base_entry, published_entry, extra_entry]
    assert doc["base"] == {
        "list_version": 2,
        "sha256": hashlib.sha256(base_raw).hexdigest(),
    }

    checked = run(
        PREPARE,
        [
            "check",
            "--base",
            str(base_path),
            "--published",
            str(published_path),
            "--candidate",
            str(out_path),
        ],
    )
    assert checked.returncode == 0, checked.stderr

    rollback = json.loads(text)
    rollback["list_version"] = 3
    rollback_path = tmp_path / "rollback.json"
    write_json(rollback_path, rollback)
    rejected = run(
        PREPARE,
        [
            "check",
            "--base",
            str(base_path),
            "--published",
            str(published_path),
            "--candidate",
            str(rollback_path),
        ],
    )
    assert rejected.returncode == 1
    assert "list_version" in rejected.stderr

    removed = json.loads(text)
    removed["revoked"] = [published_entry, extra_entry]
    removed_path = tmp_path / "removed.json"
    write_json(removed_path, removed)
    removal = run(
        PREPARE,
        [
            "check",
            "--base",
            str(base_path),
            "--published",
            str(published_path),
            "--candidate",
            str(removed_path),
        ],
    )
    assert removal.returncode == 1
    assert "superset" in removal.stderr


def bundle_for(kind: str, integrated: int) -> dict:
    if kind == "payload":
        return {"rekorBundle": {"Payload": {"integratedTime": integrated}}}
    return {"verificationMaterial": {"tlogEntries": [{"integratedTime": str(integrated)}]}}


@pytest.mark.parametrize("kind", ["payload", "tlog"])
@pytest.mark.parametrize(
    "delta,expect_ok",
    [
        (0, True),
        (300, True),
        (-3600, True),
        (301, False),
        (-3601, False),
    ],
)
def test_check_time_window(tmp_path: Path, kind: str, delta: int, expect_ok: bool) -> None:
    doc_path = tmp_path / "doc.json"
    bundle_path = tmp_path / "bundle.json"
    write_json(doc_path, {"issued_at": ISSUED})
    write_json(bundle_path, bundle_for(kind, ISSUED_UNIX - delta))
    flag = "--doc" if kind == "payload" else "--list"
    result = run(
        PREPARE,
        ["check-time", flag, str(doc_path), "--bundle", str(bundle_path)],
    )
    if expect_ok:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode == 1
        assert "integrated time" in result.stderr


def test_check_time_missing_integrated_time(tmp_path: Path) -> None:
    doc_path = tmp_path / "doc.json"
    bundle_path = tmp_path / "bundle.json"
    write_json(doc_path, {"issued_at": ISSUED})
    write_json(bundle_path, {"verificationMaterial": {"tlogEntries": []}})
    result = run(
        PREPARE,
        ["check-time", "--doc", str(doc_path), "--bundle", str(bundle_path)],
    )
    assert result.returncode == 1
    assert "no integrated time" in result.stderr


def list_body(base: dict | None) -> dict:
    doc = {
        "ldtt_spec": "0.2.0",
        "issuer": "LDTT",
        "list_version": 1,
        "issued_at": ISSUED,
        "revoked": [entry("c1", "compromised")],
    }
    if base is not None:
        doc["base"] = base
    return doc


def test_validator_require_base_vs_forbid_base(tmp_path: Path) -> None:
    pointer = {"list_version": 1, "sha256": HEX64}
    with_base = tmp_path / "with.json"
    without_base = tmp_path / "without.json"
    write_json(with_base, list_body(pointer))
    write_json(without_base, list_body(None))

    require_ok = run(VALIDATE, ["--require-base", str(with_base)])
    assert require_ok.returncode == 0, require_ok.stderr
    require_missing = run(VALIDATE, ["--require-base", str(without_base)])
    assert require_missing.returncode == 1
    assert "base" in require_missing.stderr

    forbid_ok = run(VALIDATE, ["--forbid-base", str(without_base)])
    assert forbid_ok.returncode == 0, forbid_ok.stderr
    forbid_present = run(VALIDATE, ["--forbid-base", str(with_base)])
    assert forbid_present.returncode == 1
    assert "absent" in forbid_present.stderr

    bad_hex = tmp_path / "bad-hex.json"
    write_json(bad_hex, list_body({"list_version": 1, "sha256": "AB" * 32}))
    bad = run(VALIDATE, ["--require-base", str(bad_hex)])
    assert bad.returncode == 1
    assert "sha256" in bad.stderr

    empty_reason = list_body(pointer)
    empty_reason["revoked"][0]["reason"] = ""
    empty_path = tmp_path / "empty-reason.json"
    write_json(empty_path, empty_reason)
    reason = run(VALIDATE, ["--require-base", str(empty_path)])
    assert reason.returncode == 1
    assert "reason" in reason.stderr
