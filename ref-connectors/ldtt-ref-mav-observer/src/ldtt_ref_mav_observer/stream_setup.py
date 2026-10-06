"""Stream setup via MAV_CMD_REQUEST_MESSAGE / SET_MESSAGE_INTERVAL (Phase 2 draft).

PX4 largely ignores REQUEST_DATA_STREAM; these two commands work on PX4 and ArduPilot.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Sequence

if TYPE_CHECKING:
    from .mavlink_client import MavlinkClient

# Common message IDs (MAVLink common.xml)
MSG_IDS = {
    "HEARTBEAT": 0,
    "SYS_STATUS": 1,
    "ATTITUDE": 30,
    "GLOBAL_POSITION_INT": 33,
    "BATTERY_STATUS": 147,
}

DEFAULT_RX = ("HEARTBEAT", "SYS_STATUS", "GLOBAL_POSITION_INT", "ATTITUDE", "BATTERY_STATUS")

# Interval in microseconds for SET_MESSAGE_INTERVAL (e.g. 10 Hz = 100_000)
DEFAULT_INTERVAL_US = 100_000


def setup_streams(
    client: "MavlinkClient",
    messages: Sequence[str] | None = None,
    interval_us: int = DEFAULT_INTERVAL_US,
) -> None:
    """Request each RX message via the two Observe-allowed commands only."""
    for name in messages or DEFAULT_RX:
        msg_id = MSG_IDS.get(name)
        if msg_id is None:
            continue
        # MAV_CMD_SET_MESSAGE_INTERVAL (511): param1=msg_id, param2=interval_us
        client.send_command_long("MAV_CMD_SET_MESSAGE_INTERVAL", param1=float(msg_id), param2=float(interval_us))
        # MAV_CMD_REQUEST_MESSAGE (512): param1=msg_id
        client.send_command_long("MAV_CMD_REQUEST_MESSAGE", param1=float(msg_id))
