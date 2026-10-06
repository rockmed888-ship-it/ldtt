"""Creator lock #2 (Phase 2): HEARTBEAT TX exempt from reads_per_s."""

import pytest

from ldtt_ref_mav_observer.allowlist import Allowlist, AllowlistError
from ldtt_ref_mav_observer.audit_log import AuditLog
from ldtt_ref_mav_observer.mavlink_client import MavlinkClient
from ldtt_ref_mav_observer.rate_limiter import EXEMPT_TX, RateLimitExceeded, RateLimiter, is_exempt

from .test_allowlist import CMDS, RX, TX, FakeConn


def _drained(rate=2):
    rl = RateLimiter(reads_per_s=rate)
    rl._tokens = 0.0
    rl._last = 1e12  # far future: no refill during test
    return rl


def test_exempt_set_is_heartbeat_only():
    assert EXEMPT_TX == frozenset({"HEARTBEAT"})
    assert is_exempt("HEARTBEAT")
    assert not is_exempt("COMMAND_LONG")
    assert not is_exempt("PARAM_REQUEST_LIST")


def test_limiter_check_skips_heartbeat_without_consuming():
    rl = RateLimiter(reads_per_s=1)
    rl._tokens = 1.0
    rl._last = 1e12
    for _ in range(100):
        rl.check(msg_name="HEARTBEAT")
    assert rl._tokens == 1.0  # untouched
    rl.check(msg_name="COMMAND_LONG")  # consumes the one token
    with pytest.raises(RateLimitExceeded):
        rl.check(msg_name="COMMAND_LONG")


def test_heartbeat_sends_when_bucket_empty(tmp_path):
    conn = FakeConn()
    audit = AuditLog(str(tmp_path / "a.jsonl"), [])
    client = MavlinkClient(conn, Allowlist(RX, TX, CMDS), _drained(), audit=audit)
    for _ in range(50):
        client.send_heartbeat()
    assert [s[0] for s in conn.mav.sent].count("HEARTBEAT") == 50
    # reads still limited
    with pytest.raises(RateLimitExceeded):
        client.send_command_long("MAV_CMD_REQUEST_MESSAGE", param1=0)
    assert "rate limit exceeded" in (tmp_path / "a.jsonl").read_text()


def test_heartbeat_still_allowlist_gated():
    conn = FakeConn()
    client = MavlinkClient(conn, Allowlist(RX, ["COMMAND_LONG"], CMDS), RateLimiter(reads_per_s=10))
    with pytest.raises(AllowlistError):
        client.send_heartbeat()
    assert conn.mav.sent == []
