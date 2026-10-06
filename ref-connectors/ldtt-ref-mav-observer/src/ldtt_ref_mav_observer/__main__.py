"""CLI entry for ldtt-ref-mav-observer (Phase 2 draft).

Corrector A1: verify revocation signatures in-process; never load unsigned lists.
Cosign-missing / verify-failed = list-unreachable (last verified until max_staleness_s,
then fail closed: warn + refuse sessions). N1: --heartbeat-hz capped at 2.
N3: --skip-revoke / --no-interval-check need LDTT_DEV=1 (else refused + audited); skips always audited.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from .allowlist import Allowlist
from .audit_log import AuditLog
from .cli import display_loop
from .config import load_manifest, validate_manifest
from .cosign_verify import find_cosign, sibling_bundle, verify_blob
from .dev_flags import DEV_ENV_VAR, DEV_ENV_VALUE, dev_mode_enabled, used_dev_flags
from .mavlink_client import MavlinkClient
from .rate_limiter import RateLimiter
from .revocation_checker import RevocationChecker, default_fetch
from .stream_setup import setup_streams

# N1: GCS keepalive ceiling (Corrector)
HEARTBEAT_HZ_MAX = 2.0


def _default_manifest() -> Path:
    return Path(__file__).resolve().parents[2] / "ldtt.yaml"


def _connector_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_list_url(manifest_url: str, override: Optional[str]) -> tuple[str, Optional[str]]:
    """Return (list_url, bundle_url).

    Spec v0.1.4: list_url may be https://, file:, or relative path.
    --revocation-list / LDTT_REVOCATION_LIST_PATH still override when set.
    Relative paths resolve against the connector root.
    """
    path = override or os.environ.get("LDTT_REVOCATION_LIST_PATH")
    if path:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = (_connector_root() / p).resolve()
        else:
            p = p.resolve()
        bundle = sibling_bundle(p)
        return str(p), str(bundle) if bundle.is_file() else None

    url = manifest_url
    # Relative path (no scheme, not absolute)
    if not url.startswith("https://") and not url.startswith("file:") and not url.startswith("/"):
        p = (_connector_root() / url).resolve()
        bundle = sibling_bundle(p)
        return str(p), str(bundle) if bundle.is_file() else None
    if url.startswith("file:"):
        p = Path(url[5:]).expanduser().resolve()
        bundle = sibling_bundle(p)
        return str(p), str(bundle) if bundle.is_file() else None
    return url, None


def _build_verify_fn(
    checker: RevocationChecker,
    *,
    key_path: Optional[Path],
    cosign_bin: Optional[str],
):
    def verify_fn(body: bytes, sig_bundle: Optional[bytes]) -> bool:
        import tempfile

        if sig_bundle is None:
            checker._last_verify_mode = "bundle_missing"  # noqa: SLF001
            return False

        with tempfile.TemporaryDirectory(prefix="ldtt-cosign-") as tmp:
            blob = Path(tmp) / "revocations.json"
            blob.write_bytes(body)
            bpath = Path(tmp) / "revocations.json.sigstore.json"
            bpath.write_bytes(sig_bundle)
            result = verify_blob(
                blob,
                bundle_path=bpath,
                key_path=key_path,
                cosign_path=cosign_bin,
            )
            checker._last_verify_mode = result.mode  # noqa: SLF001
            checker.state.cosign_mode = result.mode
            return result.ok

    return verify_fn


def _run_revocation_check(revoke: RevocationChecker, audit: AuditLog, label: str) -> str:
    try:
        outcome = revoke.check()
    except Exception as exc:  # noqa: BLE001
        audit.revocation_check(outcome="error", error=str(exc), when=label)
        raise
    audit.revocation_check(
        outcome=outcome,
        list_version=revoke.state.list_version,
        cosign_mode=revoke.state.cosign_mode,
        when=label,
    )
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LDTT Phase 2 Observe MAVLink reference connector")
    parser.add_argument("--manifest", type=Path, default=_default_manifest())
    parser.add_argument("--connection", default="udpin:127.0.0.1:14550", help="pymavlink connection string")
    parser.add_argument(
        "--skip-revoke",
        action="store_true",
        help=f"DEV ONLY (requires {DEV_ENV_VAR}={DEV_ENV_VALUE}): skip revocation check; audited; not evidence-eligible",
    )
    parser.add_argument("--max-messages", type=int, default=None)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--revocation-list",
        type=str,
        default=None,
        help="Local path to revocations.json (overrides manifest list_url)",
    )
    parser.add_argument(
        "--cosign-key",
        type=str,
        default=None,
        help="Public key for local-key bundle verify (default: placeholders/keys/ldtt-placeholder.pub).",
    )
    parser.add_argument("--audit-path", type=str, default=None, help="Override audit_log.path")
    parser.add_argument(
        "--no-interval-check",
        action="store_true",
        help=f"DEV ONLY (requires {DEV_ENV_VAR}={DEV_ENV_VALUE}): disable background revocation interval; audited",
    )
    parser.add_argument(
        "--wire-capture",
        type=str,
        default=None,
        help="Evidence (E8): write JSON of every MAVLink msg actually written to the link "
        "(decoded from wire bytes) and every raw RX type seen before filtering.",
    )
    parser.add_argument(
        "--heartbeat-hz",
        type=float,
        default=1.0,
        help=f"GCS keepalive HEARTBEAT rate (0=off, max {HEARTBEAT_HZ_MAX}). Exempt from reads_per_s.",
    )
    parser.add_argument("--wait-heartbeat-s", type=float, default=0.0, help="Wait up to N s for vehicle HEARTBEAT before stream setup (0=skip)")
    args = parser.parse_args(argv)

    if args.heartbeat_hz < 0 or args.heartbeat_hz > HEARTBEAT_HZ_MAX:
        print(
            f"--heartbeat-hz must be in [0, {HEARTBEAT_HZ_MAX}] (got {args.heartbeat_hz})",
            file=sys.stderr,
        )
        return 2

    doc = load_manifest(args.manifest)
    errs = validate_manifest(doc)
    if errs:
        print("ldtt.yaml INVALID:", file=sys.stderr)
        for e in errs:
            print(" -", e, file=sys.stderr)
        return 2
    print("ldtt.yaml validates against schema (E1 path)")

    if args.validate_only:
        return 0

    level = doc["level"]
    mav = doc["transport"]["mavlink"]
    connector = doc["connector"]
    audit_path = args.audit_path or doc["audit_log"]["path"]
    audit = AuditLog(audit_path, doc["audit_log"]["includes"])

    # N3: dev-only flags require LDTT_DEV=1; otherwise refuse (audited) before any session.
    dev_flags = used_dev_flags(skip_revoke=args.skip_revoke, no_interval_check=args.no_interval_check)
    if dev_flags and not dev_mode_enabled():
        print(
            f"REFUSED: {', '.join(dev_flags)} are dev-only and require {DEV_ENV_VAR}={DEV_ENV_VALUE}. "
            "Release/evidence runs must not weaken revocation (C4).",
            file=sys.stderr,
        )
        audit.refuse(
            reason="dev_only_flag_without_dev_mode",
            flags=dev_flags,
            dev_env=DEV_ENV_VAR,
            connector_id=connector["id"],
        )
        return 2
    dev_mode = bool(dev_flags)
    session_extra = {"dev_mode": True, "evidence_eligible": False, "dev_flags": dev_flags} if dev_mode else {}
    if dev_mode:
        print(
            f"WARN: DEV MODE ({DEV_ENV_VAR}={DEV_ENV_VALUE}) with {', '.join(dev_flags)} — "
            "revocation weakened; this run is NOT evidence-eligible.",
            file=sys.stderr,
        )
    audit.session(
        action="start", connector_id=connector["id"], version=connector["version"], phase="Phase 2", **session_extra
    )
    audit.scope_grant(scopes=list(doc["scopes"]))
    audit.egress_opt_in(enabled=False)

    list_url, bundle_url = _resolve_list_url(doc["revocation"]["list_url"], args.revocation_list)
    default_pub = _connector_root() / "placeholders" / "keys" / "ldtt-placeholder.pub"
    key_path = Path(args.cosign_key).expanduser() if args.cosign_key else (
        default_pub if default_pub.is_file() else None
    )
    cosign_bin = find_cosign()

    revoke = RevocationChecker(
        list_url=list_url,
        connector_id=connector["id"],
        version=connector["version"],
        digest=doc["build"]["artifact_digest"],
        max_staleness_s=int(doc["revocation"]["max_staleness_s"]),
        fetch_fn=default_fetch,
        cache_path=Path.home() / ".ldtt" / "cache" / f"{connector['id']}.revocations.json",
        bundle_url=bundle_url,
    )
    # A1-r: wire verify_fn before load_cache so cache is re-verified
    revoke.verify_fn = _build_verify_fn(revoke, key_path=key_path, cosign_bin=cosign_bin)
    revoke.load_cache()

    halt = threading.Event()

    if not args.skip_revoke:
        try:
            outcome = _run_revocation_check(revoke, audit, "startup")
        except Exception as exc:  # noqa: BLE001
            print(f"revocation check error: {exc}", file=sys.stderr)
            return 3

        if revoke.is_fail_closed:
            print(
                f"REVOKED/FAIL-CLOSED ({outcome}): Observe warns operator; "
                "no egress to stop; refusing session / halt.",
                file=sys.stderr,
            )
            audit.deny(reason=f"revocation fail-closed: {outcome}", outcome=outcome)
            audit.session(action="stop", reason=outcome)
            return 4
        print(f"revocation check: {outcome} (cosign={revoke.state.cosign_mode})")
    else:
        # N3: always audit a skipped revocation_check (never silent)
        audit.revocation_check(
            outcome="skipped_dev", when="startup", flag="--skip-revoke", dev_mode=True, evidence_eligible=False
        )

    # Background interval re-check (C4)
    stop_event = threading.Event()
    interval = int(doc["revocation"]["check_interval_s"])

    def _interval_loop() -> None:
        while not stop_event.wait(interval):
            try:
                outcome = _run_revocation_check(revoke, audit, "interval")
                if revoke.is_fail_closed:
                    print(
                        f"WARN: revocation fail-closed on interval ({outcome}); "
                        "halting session (Observe: no egress).",
                        file=sys.stderr,
                    )
                    audit.deny(reason=f"revocation fail-closed: {outcome}", outcome=outcome, when="interval")
                    halt.set()
                    stop_event.set()
            except Exception as exc:  # noqa: BLE001
                audit.revocation_check(outcome="error", error=str(exc), when="interval")

    interval_thread = None
    if args.skip_revoke or args.no_interval_check:
        # N3: audit the interval skip too (implied by --skip-revoke)
        audit.revocation_check(
            outcome="interval_skipped_dev",
            when="interval",
            flag="--no-interval-check" if args.no_interval_check else "--skip-revoke",
            check_interval_s=interval,
            dev_mode=True,
            evidence_eligible=False,
        )
    elif interval > 0:
        interval_thread = threading.Thread(target=_interval_loop, name="ldtt-revoke-interval", daemon=True)
        interval_thread.start()

    allowlist = Allowlist(mav["rx_allowlist"], mav["tx_allowlist"], mav["command_allowlist"])
    limiter = RateLimiter(reads_per_s=float(doc["rate_limits"]["reads_per_s"]))

    if doc["transport"]["kind"] == "mavlink2":
        os.environ.setdefault("MAVLINK20", "1")
    try:
        from pymavlink import mavutil
    except ImportError:
        print("pymavlink required", file=sys.stderr)
        return 5

    conn = mavutil.mavlink_connection(args.connection, source_system=255, source_component=190)
    client = MavlinkClient(conn, allowlist, limiter, audit=audit)

    capture = None
    if args.wire_capture:
        capture = _install_wire_capture(conn, client, mavutil)

    print(f"Connected ({args.connection}).")
    if args.wait_heartbeat_s > 0:
        hb = conn.wait_heartbeat(timeout=args.wait_heartbeat_s)
        if hb is None:
            print("no vehicle HEARTBEAT within timeout", file=sys.stderr)
            audit.session(action="stop", reason="no_heartbeat")
            return 6
        client.target_system = conn.target_system
        client.target_component = conn.target_component or 1
        if capture is not None:
            capture["rx_types"]["HEARTBEAT"] = capture["rx_types"].get("HEARTBEAT", 0) + 1
            capture["vehicle_heartbeat"] = {
                "type": hb.type, "autopilot": hb.autopilot, "mavlink_version": hb.mavlink_version,
                "sysid": conn.target_system, "compid": conn.target_component,
            }
        print(f"Vehicle HEARTBEAT sysid={conn.target_system} compid={conn.target_component} type={hb.type} autopilot={hb.autopilot}")

    hb_stop = threading.Event()
    hb_thread = None
    if args.heartbeat_hz > 0:
        def _hb_loop() -> None:
            period = 1.0 / args.heartbeat_hz
            while not hb_stop.is_set() and not halt.is_set():
                try:
                    client.send_heartbeat()
                except Exception as exc:  # noqa: BLE001
                    print(f"heartbeat TX note: {exc}", file=sys.stderr)
                hb_stop.wait(period)
        hb_thread = threading.Thread(target=_hb_loop, name="ldtt-gcs-heartbeat", daemon=True)
        hb_thread.start()

    print("Setting up streams (Observe read cmds only: REQUEST_MESSAGE / SET_MESSAGE_INTERVAL)...")
    print("TX locked out: REQUEST_DATA_STREAM, LOG_REQUEST_* (Phase 2 creator locks)")
    try:
        setup_streams(client)
    except Exception as exc:  # noqa: BLE001
        print(f"stream setup note: {exc}", file=sys.stderr)

    print("Local display only — Ctrl+C to stop. No egress.")
    try:
        display_loop(client, max_messages=args.max_messages, halt=halt)
    except KeyboardInterrupt:
        pass
    hb_stop.set()
    stop_event.set()
    if hb_thread is not None:
        hb_thread.join(timeout=2)
    reason = "operator"
    if halt.is_set():
        reason = "revocation_fail_closed"
    elif args.max_messages is not None:
        reason = "max_messages"
    audit.session(action="stop", reason=reason)
    if capture is not None:
        import json as _json

        Path(args.wire_capture).write_text(_json.dumps(capture, indent=2, sort_keys=True) + "\n")
    return 4 if halt.is_set() else 0


def _install_wire_capture(conn, client, mavutil):
    """Wrap conn.write to decode every outbound frame actually put on the link."""
    from pymavlink.dialects.v20 import ardupilotmega as mavlink2

    capture = {"tx": [], "tx_counts": {}, "rx_types": {}, "rx_dropped_by_filter": {}, "command_acks": [], "tx_frame_magic": {}}
    parser = mavlink2.MAVLink(None)
    parser.robust_parsing = True
    orig_write = conn.write
    lock = threading.Lock()

    def write(buf):
        with lock:
            b = bytes(buf)
            if b:
                key = {0xFD: "mavlink2_0xFD", 0xFE: "mavlink1_0xFE"}.get(b[0], hex(b[0]))
                capture["tx_frame_magic"][key] = capture["tx_frame_magic"].get(key, 0) + 1
            try:
                msgs = parser.parse_buffer(bytes(buf)) or []
            except Exception as exc:  # noqa: BLE001
                msgs = []
                capture["tx"].append({"decode_error": str(exc)})
            for m in msgs:
                name = m.get_type()
                rec = {"msg": name}
                if name == "COMMAND_LONG":
                    rec.update(command=m.command, param1=m.param1, param2=m.param2)
                capture["tx"].append(rec)
                capture["tx_counts"][name] = capture["tx_counts"].get(name, 0) + 1
        return orig_write(buf)

    conn.write = write

    def rx_obs(name, msg):
        with lock:
            if name == "COMMAND_ACK":
                capture["command_acks"].append({"command": msg.command, "result": msg.result})
            capture["rx_types"][name] = capture["rx_types"].get(name, 0) + 1
            if not client.allowlist.allow_rx(name):
                capture["rx_dropped_by_filter"][name] = capture["rx_dropped_by_filter"].get(name, 0) + 1

    client.rx_observer = rx_obs
    return capture


if __name__ == "__main__":
    raise SystemExit(main())
