"""N3 (Corrector): --skip-revoke / --no-interval-check are dev-only (LDTT_DEV=1) and audited."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ldtt_ref_mav_observer.__main__ import main
from ldtt_ref_mav_observer.dev_flags import (
    DEV_ENV_VAR,
    SKIP_OUTCOMES,
    dev_mode_enabled,
    used_dev_flags,
)

ROOT = Path(__file__).resolve().parents[1]
# udpout to a closed local port: writes succeed, nothing listens; --max-messages 0 exits at once
_CONN = ["--connection", "udpout:127.0.0.1:14599", "--max-messages", "0", "--heartbeat-hz", "0"]
BASE: list[str] = []  # filled per-test by the signed_list fixture


def _fresh_signed_list(d: Path) -> list[str]:
    """Fresh revocation list signed with an ephemeral P-256 key (cosign local-key bundle shape).

    Keeps N3 tests independent of the published placeholder list's issued_at / staleness.
    """
    import base64
    from datetime import datetime, timezone

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = json.dumps({"ldtt_spec": "0.1.4", "issuer": "LDTT-test", "list_version": 1, "issued_at": now, "revoked": []}).encode()
    lst = d / "revocations.json"
    lst.write_bytes(body)
    sig = key.sign(body, ec.ECDSA(hashes.SHA256()))
    (d / "revocations.json.sigstore.json").write_text(json.dumps({"base64Signature": base64.b64encode(sig).decode()}))
    pub = d / "test.pub"
    pub.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return ["--revocation-list", str(lst), "--cosign-key", str(pub)]


def _events(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.is_file() else []


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    # keep revocation cache out of the real ~/.ldtt
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv(DEV_ENV_VAR, raising=False)
    monkeypatch.delenv("LDTT_REVOCATION_LIST_PATH", raising=False)
    sig_dir = tmp_path / "signed"
    sig_dir.mkdir()
    BASE[:] = _CONN + _fresh_signed_list(sig_dir)


def test_dev_mode_requires_exact_value():
    assert dev_mode_enabled({DEV_ENV_VAR: "1"})
    for v in ("", "0", "true", "yes", "2"):
        assert not dev_mode_enabled({DEV_ENV_VAR: v})
    assert not dev_mode_enabled({})


def test_used_dev_flags():
    assert used_dev_flags(skip_revoke=False, no_interval_check=False) == []
    assert used_dev_flags(skip_revoke=True, no_interval_check=True) == ["--skip-revoke", "--no-interval-check"]


@pytest.mark.parametrize("flag", ["--skip-revoke", "--no-interval-check"])
def test_flag_refused_without_dev_env(tmp_path, flag, capsys):
    audit = tmp_path / "a.jsonl"
    rc = main(BASE + ["--audit-path", str(audit), flag])
    assert rc == 2
    assert "dev-only" in capsys.readouterr().err
    ev = _events(audit)
    assert [e["event"] for e in ev] == ["refuse"]
    assert ev[0]["reason"] == "dev_only_flag_without_dev_mode"
    assert ev[0]["flags"] == [flag]
    # no session started, no revocation_check written
    assert not any(e["event"] in ("session", "revocation_check") for e in ev)


@pytest.mark.parametrize("val", ["0", "true", ""])
def test_flag_refused_with_wrong_dev_value(tmp_path, monkeypatch, val):
    monkeypatch.setenv(DEV_ENV_VAR, val)
    audit = tmp_path / "a.jsonl"
    assert main(BASE + ["--audit-path", str(audit), "--skip-revoke"]) == 2


def test_skip_revoke_with_dev_env_audits_skip(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(DEV_ENV_VAR, "1")
    audit = tmp_path / "a.jsonl"
    rc = main(BASE + ["--audit-path", str(audit), "--skip-revoke"])
    assert rc == 0
    assert "NOT evidence-eligible" in capsys.readouterr().err
    ev = _events(audit)
    start = next(e for e in ev if e["event"] == "session" and e["action"] == "start")
    assert start["dev_mode"] is True and start["evidence_eligible"] is False
    rc_events = [e for e in ev if e["event"] == "revocation_check"]
    outcomes = {e["outcome"] for e in rc_events}
    assert outcomes == {"skipped_dev", "interval_skipped_dev"}  # interval implied
    assert all(e["evidence_eligible"] is False for e in rc_events)
    # no real check ran
    assert not any(e.get("outcome") == "ok" for e in rc_events)


def test_no_interval_check_with_dev_env_runs_startup_and_audits_interval_skip(tmp_path, monkeypatch):
    monkeypatch.setenv(DEV_ENV_VAR, "1")
    audit = tmp_path / "a.jsonl"
    rc = main(BASE + ["--audit-path", str(audit), "--no-interval-check"])
    assert rc == 0
    ev = [e for e in _events(audit) if e["event"] == "revocation_check"]
    assert ev[0]["outcome"] == "ok" and ev[0]["when"] == "startup"  # startup still verified
    skip = [e for e in ev if e["outcome"] == "interval_skipped_dev"]
    assert len(skip) == 1 and skip[0]["flag"] == "--no-interval-check"


def test_release_run_has_no_dev_markers(tmp_path):
    audit = tmp_path / "a.jsonl"
    rc = main(BASE + ["--audit-path", str(audit)])
    assert rc == 0
    ev = _events(audit)
    assert not any(e.get("dev_mode") for e in ev)
    assert not any(e.get("outcome") in SKIP_OUTCOMES for e in ev)
    assert any(e["event"] == "revocation_check" and e["outcome"] == "ok" for e in ev)


def _checker():
    spec = importlib.util.spec_from_file_location("chk", ROOT / "scripts" / "check_evidence_no_dev_flags.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_evidence_checker_flags_skip_runs(tmp_path):
    chk = _checker()
    (tmp_path / "e5.jsonl").write_text(json.dumps({"event": "revocation_check", "outcome": "skipped_dev"}) + "\n")
    (tmp_path / "stdout.txt").write_text("$ python -m ldtt_ref_mav_observer --no-interval-check\n")
    probs = chk.scan(tmp_path)
    assert len(probs) == 2
    # superseded dir is excluded
    sup = tmp_path / "x"
    sup.mkdir()
    (sup / "superseded-dev-flags").mkdir()
    assert chk.scan(sup) == []


def test_repo_evidence_does_not_rely_on_skip_flags():
    """E6/E5/E8 evidence in-tree must come from runs WITHOUT dev-only flags."""
    assert _checker().scan(ROOT / "evidence") == []
