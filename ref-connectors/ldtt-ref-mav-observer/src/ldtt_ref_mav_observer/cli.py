"""Local CLI telemetry display — no egress (Phase 2 draft)."""

from __future__ import annotations

import sys
import threading
from typing import Any, Optional, TextIO


def format_msg(msg: Any) -> str:
    name = msg.get_type()
    if name == "HEARTBEAT":
        return f"HEARTBEAT type={getattr(msg, 'type', '?')} autopilot={getattr(msg, 'autopilot', '?')} base_mode={getattr(msg, 'base_mode', '?')}"
    if name == "SYS_STATUS":
        return f"SYS_STATUS voltage_battery={getattr(msg, 'voltage_battery', '?')} current_battery={getattr(msg, 'current_battery', '?')}"
    if name == "GLOBAL_POSITION_INT":
        lat = getattr(msg, "lat", 0) / 1e7
        lon = getattr(msg, "lon", 0) / 1e7
        alt = getattr(msg, "alt", 0) / 1000
        return f"GLOBAL_POSITION_INT lat={lat:.6f} lon={lon:.6f} alt_m={alt:.1f}"
    if name == "ATTITUDE":
        return f"ATTITUDE roll={getattr(msg, 'roll', 0):.3f} pitch={getattr(msg, 'pitch', 0):.3f} yaw={getattr(msg, 'yaw', 0):.3f}"
    if name == "BATTERY_STATUS":
        return f"BATTERY_STATUS voltages[0]={getattr(msg, 'voltages', [None])[0]} remaining={getattr(msg, 'battery_remaining', '?')}"
    return f"{name}"


def display_loop(
    client: Any,
    out: TextIO = sys.stdout,
    max_messages: Optional[int] = None,
    halt: Optional[threading.Event] = None,
) -> int:
    """Poll filtered RX and print. Returns count displayed.

    ``halt`` (optional): when set, leave the loop so revocation fail-closed can stop the session.
    """
    n = 0
    while max_messages is None or n < max_messages:
        if halt is not None and halt.is_set():
            break
        msg = client.recv_filtered(blocking=True, timeout=1.0)
        if msg is None:
            continue
        out.write(format_msg(msg) + "\n")
        out.flush()
        n += 1
    return n
