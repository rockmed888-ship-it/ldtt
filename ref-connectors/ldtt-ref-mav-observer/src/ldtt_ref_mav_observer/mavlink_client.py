"""MAVLink 2 client with RX filter + TX allowlist enforcement (Phase 2 draft)."""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

from .allowlist import Allowlist, AllowlistError, MAV_CMD_NUMERIC
from .audit_log import AuditLog
from .rate_limiter import RateLimitExceeded, RateLimiter, is_exempt

RefuseCallback = Callable[[str, dict], None]


class MavlinkClient:
    """Wraps a pymavlink connection (or a test double).

    Production: pass connection from mavutil.mavlink_connection(...).
    Tests: pass a FakeConnection with recv_match / mav.* helpers.
    """

    def __init__(
        self,
        connection: Any,
        allowlist: Allowlist,
        rate_limiter: RateLimiter,
        audit: Optional[AuditLog] = None,
        system_id: int = 255,
        component_id: int = 190,
    ) -> None:
        self.conn = connection
        self.allowlist = allowlist
        self.rate_limiter = rate_limiter
        self.audit = audit
        self.system_id = system_id
        self.component_id = component_id
        self.target_system = 1
        self.target_component = 1
        self._send_lock = threading.Lock()
        # Optional evidence hook: called with every raw RX type BEFORE filtering.
        self.rx_observer: Optional[Callable[[str, Any], None]] = None

    def recv_filtered(self, blocking: bool = False, timeout: float = 1.0) -> Optional[Any]:
        msg = self.conn.recv_match(blocking=blocking, timeout=timeout)
        if msg is None:
            return None
        name = msg.get_type()
        if self.rx_observer is not None:
            self.rx_observer(name, msg)
        if name == "BAD_DATA":
            return None
        if not self.allowlist.allow_rx(name):
            return None
        return msg

    def send_message(self, msg_name: str, **fields: Any) -> None:
        """Send a named message after allowlist + rate checks."""
        command = fields.get("command")
        try:
            self.allowlist.check_tx(msg_name, command=command)
            # Creator lock #2: HEARTBEAT is keepalive, exempt from reads_per_s.
            self.rate_limiter.check(msg_name=msg_name)
        except (AllowlistError, RateLimitExceeded) as exc:
            if self.audit:
                self.audit.refuse(str(exc), msg=msg_name, command=command)
            raise

        mav = self.conn.mav
        encoder = getattr(mav, f"{msg_name.lower()}_send", None)
        if encoder is None:
            # Fallback for tests / minimal fakes
            send = getattr(self.conn, "send_named", None)
            if send:
                send(msg_name, fields)
                return
            raise AttributeError(f"connection cannot encode {msg_name}")
        with self._send_lock:
            encoder(**fields)

    def send_heartbeat(self) -> None:
        """GCS keepalive HEARTBEAT (MAV_TYPE_GCS, MAV_AUTOPILOT_INVALID).

        Allowlist-checked; NOT counted against reads_per_s (creator lock #2).
        """
        self.send_message(
            "HEARTBEAT",
            type=6,  # MAV_TYPE_GCS
            autopilot=8,  # MAV_AUTOPILOT_INVALID
            base_mode=0,
            custom_mode=0,
            system_status=0,
        )

    def send_command_long(
        self,
        command: str | int,
        param1: float = 0,
        param2: float = 0,
        param3: float = 0,
        param4: float = 0,
        param5: float = 0,
        param6: float = 0,
        param7: float = 0,
        confirmation: int = 0,
    ) -> None:
        if isinstance(command, str):
            cmd_id = MAV_CMD_NUMERIC.get(command)
            cmd_name: str | int = command
        else:
            cmd_id = int(command)
            cmd_name = cmd_id

        try:
            # Unknown names fail allowlist (command not in command_allowlist) -> refuse audited
            self.allowlist.check_tx("COMMAND_LONG", command=cmd_name)
            if cmd_id is None:
                raise AllowlistError(f"TX refused: unknown command name {command}")
            self.rate_limiter.check(msg_name="COMMAND_LONG")
        except (AllowlistError, RateLimitExceeded) as exc:
            if self.audit:
                self.audit.refuse(str(exc), msg="COMMAND_LONG", command=cmd_name)
            raise

        mav = self.conn.mav
        if hasattr(mav, "command_long_send"):
            with self._send_lock:
                mav.command_long_send(
                    self.target_system,
                    self.target_component,
                    cmd_id,
                    confirmation,
                    param1,
                    param2,
                    param3,
                    param4,
                    param5,
                    param6,
                    param7,
                )
        elif hasattr(self.conn, "send_named"):
            self.conn.send_named(
                "COMMAND_LONG",
                {"command": cmd_id, "param1": param1, "param2": param2},
            )
        else:
            raise AttributeError("connection cannot send COMMAND_LONG")
