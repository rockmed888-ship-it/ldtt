"""Creator lock #3 (Phase 2): includes = minimum set; refuse/deny always writable."""

import json

import pytest

from ldtt_ref_mav_observer.allowlist import Allowlist, AllowlistError
from ldtt_ref_mav_observer.audit_log import ALWAYS_ALLOWED_EVENTS, AuditLog
from ldtt_ref_mav_observer.mavlink_client import MavlinkClient
from ldtt_ref_mav_observer.rate_limiter import RateLimiter

from .test_allowlist import CMDS, RX, TX, FakeConn

SCHEMA_INCLUDES = ["session", "scope_grant", "egress_opt_in", "revocation_check"]


def _events(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def test_refuse_and_deny_not_in_includes_but_written(tmp_path):
    p = tmp_path / "a.jsonl"
    audit = AuditLog(str(p), SCHEMA_INCLUDES)
    assert "refuse" not in SCHEMA_INCLUDES and "deny" not in SCHEMA_INCLUDES
    assert ALWAYS_ALLOWED_EVENTS >= {"refuse", "deny"}
    audit.refuse("TX refused: test", msg="PARAM_SET")
    audit.deny("revoked", outcome="revoked")
    ev = _events(p)
    assert [e["event"] for e in ev] == ["refuse", "deny"]
    assert audit.is_writable("refuse") and audit.is_writable("deny")


def test_refuse_written_even_with_empty_includes(tmp_path):
    p = tmp_path / "a.jsonl"
    AuditLog(str(p), []).refuse("x")
    assert _events(p)[0]["event"] == "refuse"


def test_includes_is_minimum_set(tmp_path):
    audit = AuditLog(str(tmp_path / "a.jsonl"), SCHEMA_INCLUDES)
    assert audit.missing_required() == SCHEMA_INCLUDES
    audit.session(action="start")
    audit.scope_grant(scopes=["observe:telemetry"])
    audit.refuse("extra")  # extra beyond minimum is fine
    assert audit.missing_required() == ["egress_opt_in", "revocation_check"]
    audit.egress_opt_in(enabled=False)
    audit.revocation_check(outcome="ok")
    assert audit.missing_required() == []


@pytest.mark.parametrize(
    "cmd", ["MAV_CMD_COMPONENT_ARM_DISARM", "MAV_CMD_NAV_TAKEOFF", 400]
)
def test_client_refuse_is_audited(tmp_path, cmd):
    p = tmp_path / "a.jsonl"
    audit = AuditLog(str(p), SCHEMA_INCLUDES)
    client = MavlinkClient(FakeConn(), Allowlist(RX, TX, CMDS), RateLimiter(reads_per_s=10), audit=audit)
    with pytest.raises(AllowlistError):
        client.send_command_long(cmd)
    ev = _events(p)
    assert ev and ev[-1]["event"] == "refuse" and ev[-1]["msg"] == "COMMAND_LONG"


@pytest.mark.parametrize("msg", ["REQUEST_DATA_STREAM", "LOG_REQUEST_LIST", "PARAM_SET"])
def test_locked_message_refuse_is_audited(tmp_path, msg):
    p = tmp_path / "a.jsonl"
    audit = AuditLog(str(p), SCHEMA_INCLUDES)
    client = MavlinkClient(FakeConn(), Allowlist(RX, TX, CMDS), RateLimiter(reads_per_s=10), audit=audit)
    with pytest.raises(AllowlistError):
        client.send_message(msg)
    assert _events(p)[-1]["event"] == "refuse"
