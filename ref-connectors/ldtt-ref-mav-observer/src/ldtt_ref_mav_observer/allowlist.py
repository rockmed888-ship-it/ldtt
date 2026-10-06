"""RX/TX/command allowlist enforcement for Observe level (Phase 2 draft).

Creator locks (Phase 2):
- REQUEST_DATA_STREAM removed from connector tx_allowlist (F8 / PX4-friendly).
- LOG_REQUEST_* omitted (scopes observe:telemetry only — least privilege).
Stream setup uses MAV_CMD_REQUEST_MESSAGE + MAV_CMD_SET_MESSAGE_INTERVAL only.
"""

from __future__ import annotations

from typing import FrozenSet, Iterable, Optional

# Connector Observe TX upper bound (schema observeTx minus Phase-2 locks).
# Schema still lists REQUEST_DATA_STREAM / LOG_REQUEST_* for other connectors;
# this reference connector must not send them.
CONNECTOR_OBSERVE_TX: FrozenSet[str] = frozenset(
    {
        "HEARTBEAT",
        "PARAM_REQUEST_READ",
        "PARAM_REQUEST_LIST",
        "MISSION_REQUEST_LIST",
        "MISSION_REQUEST_INT",
        "MISSION_ACK",
        "COMMAND_LONG",
    }
)

# Hard-denied even if a drifted manifest tries to re-add them
LOCKED_OUT_TX: FrozenSet[str] = frozenset(
    {
        "REQUEST_DATA_STREAM",
        "LOG_REQUEST_LIST",
        "LOG_REQUEST_DATA",
        "LOG_REQUEST_END",
    }
)

# Schema $defs/readCmd — Observe command_allowlist only
OBSERVE_COMMAND_DEFAULT: FrozenSet[str] = frozenset(
    {
        "MAV_CMD_REQUEST_MESSAGE",
        "MAV_CMD_SET_MESSAGE_INTERVAL",
    }
)

# Numeric IDs used by pymavlink COMMAND_LONG (common.xml)
MAV_CMD_NUMERIC = {
    "MAV_CMD_REQUEST_MESSAGE": 512,
    "MAV_CMD_SET_MESSAGE_INTERVAL": 511,
}
NUMERIC_TO_MAV_CMD = {v: k for k, v in MAV_CMD_NUMERIC.items()}

# Back-compat alias for tests / docs that referenced OBSERVE_TX_DEFAULT
OBSERVE_TX_DEFAULT = CONNECTOR_OBSERVE_TX


class AllowlistError(PermissionError):
    """Raised when a send would violate the Observe allowlists."""


class Allowlist:
    """Enforces manifest rx/tx/command allowlists at runtime."""

    def __init__(
        self,
        rx: Iterable[str],
        tx: Iterable[str],
        commands: Iterable[str],
    ) -> None:
        self.rx = frozenset(rx)
        self.tx = frozenset(tx)
        self.commands = frozenset(commands)
        locked = self.tx & LOCKED_OUT_TX
        if locked:
            raise ValueError(
                f"tx_allowlist contains Phase-2 locked-out messages: {locked}"
            )
        # Defense in depth: never widen beyond connector Observe set
        if not self.tx.issubset(CONNECTOR_OBSERVE_TX):
            raise ValueError(
                f"tx_allowlist outside connector Observe set: {self.tx - CONNECTOR_OBSERVE_TX}"
            )
        if not self.commands.issubset(OBSERVE_COMMAND_DEFAULT):
            raise ValueError(
                f"command_allowlist outside Observe read cmds: {self.commands - OBSERVE_COMMAND_DEFAULT}"
            )

    def allow_rx(self, msg_name: str) -> bool:
        return msg_name in self.rx

    def check_tx(self, msg_name: str, command: Optional[str | int] = None) -> None:
        if msg_name in LOCKED_OUT_TX:
            raise AllowlistError(f"TX refused: {msg_name} locked out (Phase 2 creator lock)")
        if msg_name not in self.tx:
            raise AllowlistError(f"TX refused: {msg_name} not in tx_allowlist")
        if msg_name == "COMMAND_LONG":
            cmd_name = self._normalize_command(command)
            if cmd_name is None or cmd_name not in self.commands:
                raise AllowlistError(
                    f"TX refused: COMMAND_LONG command {command!r} not in command_allowlist"
                )

    def allow_tx(self, msg_name: str, command: Optional[str | int] = None) -> bool:
        try:
            self.check_tx(msg_name, command)
            return True
        except AllowlistError:
            return False

    @staticmethod
    def _normalize_command(command: Optional[str | int]) -> Optional[str]:
        if command is None:
            return None
        if isinstance(command, str):
            return command
        return NUMERIC_TO_MAV_CMD.get(int(command))
