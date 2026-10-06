"""Unit tests: Observe TX/command allowlist enforcement (Phase 2)."""

import pytest

from ldtt_ref_mav_observer.allowlist import (
    LOCKED_OUT_TX,
    Allowlist,
    AllowlistError,
)
from ldtt_ref_mav_observer.mavlink_client import MavlinkClient
from ldtt_ref_mav_observer.rate_limiter import RateLimiter


RX = ["HEARTBEAT", "SYS_STATUS", "GLOBAL_POSITION_INT", "ATTITUDE", "BATTERY_STATUS"]
# Phase 2 locks: no REQUEST_DATA_STREAM, no LOG_REQUEST_*
TX = ["HEARTBEAT", "PARAM_REQUEST_LIST", "COMMAND_LONG"]
CMDS = ["MAV_CMD_REQUEST_MESSAGE", "MAV_CMD_SET_MESSAGE_INTERVAL"]


class FakeMav:
    def __init__(self):
        self.sent = []

    def command_long_send(self, *args, **kwargs):
        self.sent.append(("COMMAND_LONG", args, kwargs))

    def heartbeat_send(self, *args, **kwargs):
        self.sent.append(("HEARTBEAT", args, kwargs))


class FakeConn:
    def __init__(self):
        self.mav = FakeMav()
        self._queue = []

    def recv_match(self, blocking=False, timeout=1.0):
        return self._queue.pop(0) if self._queue else None


def test_rx_filter():
    al = Allowlist(RX, TX, CMDS)
    assert al.allow_rx("HEARTBEAT")
    assert not al.allow_rx("RC_CHANNELS")


def test_tx_refuse_param_set():
    al = Allowlist(RX, TX, CMDS)
    with pytest.raises(AllowlistError):
        al.check_tx("PARAM_SET")


def test_tx_refuse_request_data_stream_locked():
    al = Allowlist(RX, TX, CMDS)
    with pytest.raises(AllowlistError):
        al.check_tx("REQUEST_DATA_STREAM")


def test_tx_refuse_log_request_locked():
    al = Allowlist(RX, TX, CMDS)
    for name in ("LOG_REQUEST_LIST", "LOG_REQUEST_DATA", "LOG_REQUEST_END"):
        with pytest.raises(AllowlistError):
            al.check_tx(name)


def test_manifest_cannot_readd_locked_tx():
    with pytest.raises(ValueError):
        Allowlist(RX, TX + ["REQUEST_DATA_STREAM"], CMDS)
    with pytest.raises(ValueError):
        Allowlist(RX, TX + ["LOG_REQUEST_LIST"], CMDS)
    assert "REQUEST_DATA_STREAM" in LOCKED_OUT_TX


def test_tx_refuse_arm_command():
    al = Allowlist(RX, TX, CMDS)
    with pytest.raises(AllowlistError):
        al.check_tx("COMMAND_LONG", command="MAV_CMD_COMPONENT_ARM_DISARM")


def test_tx_allow_request_message():
    al = Allowlist(RX, TX, CMDS)
    al.check_tx("COMMAND_LONG", command="MAV_CMD_REQUEST_MESSAGE")
    al.check_tx("COMMAND_LONG", command=512)  # numeric


def test_client_refuses_and_allows():
    al = Allowlist(RX, TX, CMDS)
    rl = RateLimiter(reads_per_s=100)
    conn = FakeConn()
    client = MavlinkClient(conn, al, rl)
    client.send_command_long("MAV_CMD_SET_MESSAGE_INTERVAL", param1=33, param2=100000)
    assert conn.mav.sent
    with pytest.raises(AllowlistError):
        client.send_command_long("MAV_CMD_NAV_TAKEOFF")


def test_manifest_cannot_widen_tx():
    with pytest.raises(ValueError):
        Allowlist(RX, TX + ["PARAM_SET"], CMDS)
