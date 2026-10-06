#!/usr/bin/env python3
"""Phase 2 REAL SITL smoke for ldtt-ref-mav-observer (E8).

Runs against a REAL ArduCopter SITL process on tcp:127.0.0.1:5760 — never the
fake HEARTBEAT peer (that is scripts/sitl_smoke.py, interim E8 only).

Backends ($0, no Docker):
  official  : ArduPilot prebuilt SITL binary from firmware.ardupilot.org
              (Copter/stable/SITL_x86_64_linux_gnu/arducopter) + copter.parm
  dronekit  : dronekit-sitl copter-3.3 (old; no SET_MESSAGE_INTERVAL/REQUEST_MESSAGE
              support, no MAVLink2) — HEARTBEAT only, cannot meet stream criterion.

Phase A: observer CLI subprocess (manifest validate, cosign+revocation, audit,
         GCS HEARTBEAT, stream setup, display) with --wire-capture.
Phase B: in-process negative TX on the same real link: REQUEST_DATA_STREAM,
         LOG_REQUEST_*, PARAM_SET, COMMAND_LONG ARM/TAKEOFF must be refused,
         audited, absent from wire; HEARTBEAT must still go out with an EMPTY
         reads_per_s bucket (creator lock #2); vehicle must remain disarmed.

Exit 0 = all SITL PASS criteria met (draft evidence; Corrector reviews via creator).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MAVLINK20", "1")

PORT = 5760
CONN = f"tcp:127.0.0.1:{PORT}"
SITL_DIR = ROOT.parents[1] / "sitl-bin"  # /workspace/ldtt/sitl-bin (outside repo)
OFFICIAL_URL = "https://firmware.ardupilot.org/Copter/stable/SITL_x86_64_linux_gnu/"
HOME = "-35.363261,149.165230,584,353"
EVID = ROOT / "evidence"
LOCKED_WIRE = {"REQUEST_DATA_STREAM", "LOG_REQUEST_LIST", "LOG_REQUEST_DATA", "LOG_REQUEST_END", "PARAM_SET"}
FORBIDDEN_CMDS = {400, 22, 176, 246}  # ARM_DISARM, NAV_TAKEOFF, DO_SET_MODE, REBOOT_SHUTDOWN


def _port_open() -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def _wait_port(t: float) -> bool:
    end = time.time() + t
    while time.time() < end:
        if _port_open():
            return True
        time.sleep(0.5)
    return False


def _fetch(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as r, dest.open("wb") as f:
        shutil.copyfileobj(r, f)


def ensure_official() -> dict:
    SITL_DIR.mkdir(parents=True, exist_ok=True)
    binp = SITL_DIR / "arducopter"
    if not binp.is_file():
        _fetch(OFFICIAL_URL + "arducopter", binp)
        binp.chmod(0o755)
    gv = SITL_DIR / "git-version.txt"
    if not gv.is_file():
        _fetch(OFFICIAL_URL + "git-version.txt", gv)
    commit = gv.read_text().split()[1]
    parm = SITL_DIR / "copter.parm"
    if not parm.is_file():
        _fetch(
            f"https://raw.githubusercontent.com/ArduPilot/ardupilot/{commit}/Tools/autotest/default_params/copter.parm",
            parm,
        )
    ver = [l for l in gv.read_text().splitlines() if l.startswith("APMVERSION")]
    return {
        "backend": "ardupilot_official_prebuilt_sitl",
        "binary_url": OFFICIAL_URL + "arducopter",
        "binary_sha256": hashlib.sha256(binp.read_bytes()).hexdigest(),
        "git_commit": commit,
        "apm_version": ver[0].split(":", 1)[1].strip() if ver else "unknown",
        "defaults": "Tools/autotest/default_params/copter.parm@" + commit,
    }


def launch(backend: str) -> tuple[subprocess.Popen | None, dict]:
    if _port_open():
        return None, {"backend": "preexisting_listener_on_5760", "note": "not launched by this script"}
    if backend == "official":
        info = ensure_official()
        run = SITL_DIR / "run"
        run.mkdir(exist_ok=True)
        # --serial0 tcp:0 (no ":wait") so the sim + EKF start before any client connects
        cmd = [str(SITL_DIR / "arducopter"), "-w", "--model", "quad", "--home", HOME, "--serial0", "tcp:0",
               "--defaults", str(SITL_DIR / "copter.parm")]
        cwd = run
    else:
        info = {"backend": "dronekit_sitl_copter_3.3"}
        cmd = [str(ROOT / ".venv" / "bin" / "dronekit-sitl"), "copter-3.3", f"--home={HOME}"]
        cwd = ROOT
    log = open("/tmp/ldtt-real-sitl.log", "w")
    proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, start_new_session=True)
    info["cmd"] = " ".join(cmd)
    if not _wait_port(30):
        proc.kill()
        raise SystemExit("SITL did not open tcp:5760")
    return proc, info


def phase_a(audit_path: Path, cap_path: Path, max_messages: int) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "ldtt_ref_mav_observer", "--manifest", str(ROOT / "ldtt.yaml"),
           "--connection", CONN,
           "--revocation-list", str(ROOT / "placeholders/revocations/revocations.json"),
           "--cosign-key", str(ROOT / "placeholders/keys/ldtt-placeholder.pub"),
           "--audit-path", str(audit_path), "--max-messages", str(max_messages),
           "--wait-heartbeat-s", "30", "--heartbeat-hz", "1",
           "--wire-capture", str(cap_path)]
    p = subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=180)
    (EVID / "e8-real-sitl-observer-stdout.txt").write_text(
        "$ " + " ".join(cmd) + "\n" + p.stdout + "\n--- stderr ---\n" + p.stderr + f"\nreturncode={p.returncode}\n")
    cap = json.loads(cap_path.read_text()) if cap_path.is_file() else {}
    lines = p.stdout.splitlines()
    gpi = [l for l in lines if l.startswith("GLOBAL_POSITION_INT")]
    return {"returncode": p.returncode, "capture": cap, "cmd": cmd[1:],
            "displayed_counts": {k: sum(1 for l in lines if l.startswith(k + " ")) for k in
                                 ("HEARTBEAT", "SYS_STATUS", "GLOBAL_POSITION_INT", "ATTITUDE", "BATTERY_STATUS")},
            "last_global_position": gpi[-1] if gpi else None,
            "revocation_line": next((l for l in lines if l.startswith("revocation check")), None)}


def phase_b(audit_path: Path) -> dict:
    from pymavlink import mavutil
    from ldtt_ref_mav_observer.__main__ import _install_wire_capture
    from ldtt_ref_mav_observer.allowlist import Allowlist, AllowlistError
    from ldtt_ref_mav_observer.audit_log import AuditLog
    from ldtt_ref_mav_observer.config import load_manifest
    from ldtt_ref_mav_observer.mavlink_client import MavlinkClient
    from ldtt_ref_mav_observer.rate_limiter import RateLimitExceeded, RateLimiter

    doc = load_manifest(ROOT / "ldtt.yaml")
    mav = doc["transport"]["mavlink"]
    al = Allowlist(mav["rx_allowlist"], mav["tx_allowlist"], mav["command_allowlist"])
    rl = RateLimiter(reads_per_s=float(doc["rate_limits"]["reads_per_s"]))
    audit = AuditLog(str(audit_path), doc["audit_log"]["includes"])
    audit.session(action="start", phase="Phase 2", test="real_sitl_negative_tx")
    conn = mavutil.mavlink_connection(CONN, source_system=255, source_component=190)
    hb = conn.wait_heartbeat(timeout=30)
    client = MavlinkClient(conn, al, rl, audit=audit)
    client.target_system = conn.target_system
    cap = _install_wire_capture(conn, client, mavutil)

    refused = {}
    attempts = [
        ("REQUEST_DATA_STREAM", lambda: client.send_message("REQUEST_DATA_STREAM", target_system=1, target_component=1, req_stream_id=0, req_message_rate=10, start_stop=1)),
        ("LOG_REQUEST_LIST", lambda: client.send_message("LOG_REQUEST_LIST", target_system=1, target_component=1, start=0, end=0xFFFF)),
        ("LOG_REQUEST_DATA", lambda: client.send_message("LOG_REQUEST_DATA", target_system=1, target_component=1, id=1, ofs=0, count=90)),
        ("LOG_REQUEST_END", lambda: client.send_message("LOG_REQUEST_END", target_system=1, target_component=1)),
        ("PARAM_SET", lambda: client.send_message("PARAM_SET", target_system=1, target_component=1, param_id=b"FENCE_ENABLE", param_value=0, param_type=9)),
        ("COMMAND_LONG:MAV_CMD_COMPONENT_ARM_DISARM", lambda: client.send_command_long("MAV_CMD_COMPONENT_ARM_DISARM", param1=1)),
        ("COMMAND_LONG:400", lambda: client.send_command_long(400, param1=1, param2=21196)),
        ("COMMAND_LONG:22_TAKEOFF", lambda: client.send_command_long(22, param7=10)),
        ("COMMAND_LONG:246_REBOOT", lambda: client.send_command_long(246, param1=1)),
    ]
    for label, fn in attempts:
        try:
            fn()
            refused[label] = "SENT (VIOLATION)"
        except AllowlistError as exc:
            refused[label] = f"refused: {exc}"

    # Creator lock #2 on the real link: drain bucket, HEARTBEAT still sends, reads do not
    rl._tokens = 0.0
    rl._last = time.monotonic() + 3600  # freeze refill for the test window
    hb_sent = 0
    for _ in range(5):
        client.send_heartbeat()
        hb_sent += 1
    try:
        client.send_command_long("MAV_CMD_REQUEST_MESSAGE", param1=0)
        read_while_empty = "SENT (bucket not enforced!)"
    except RateLimitExceeded as exc:
        read_while_empty = f"rate-limited: {exc}"

    # Vehicle must stay disarmed
    armed_seen, hbs = False, 0
    end = time.time() + 4
    while time.time() < end:
        m = conn.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
        if m is not None and m.get_srcSystem() == conn.target_system:
            hbs += 1
            armed_seen |= bool(m.base_mode & 128)
    audit.session(action="stop", reason="test_complete")
    conn.close()
    return {"vehicle_hb_type": hb.type if hb else None, "refused": refused,
            "heartbeat_sent_with_empty_bucket": hb_sent, "read_with_empty_bucket": read_while_empty,
            "vehicle_heartbeats_after": hbs, "vehicle_armed_seen": armed_seen, "wire": cap}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["official", "dronekit"], default="official")
    ap.add_argument("--warmup-s", type=float, default=45.0, help="let EKF/GPS settle before Phase A")
    ap.add_argument("--max-messages", type=int, default=300)
    ap.add_argument("--keep-sitl", action="store_true")
    ap.add_argument("--evidence-dir", type=Path, default=None, help="override evidence output dir")
    a = ap.parse_args()
    global EVID
    if a.evidence_dir:
        EVID = a.evidence_dir
    EVID.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    proc, info = launch(a.backend)
    try:
        if proc is not None:
            time.sleep(a.warmup_s)
        audit_a = EVID / "e5-real-sitl-audit.jsonl"
        audit_b = EVID / "e8-real-sitl-refuse-audit.jsonl"
        for f in (audit_a, audit_b):
            f.unlink(missing_ok=True)
        A = phase_a(audit_a, EVID / "e8-real-sitl-wire-capture.json", a.max_messages)
        time.sleep(1.0)
        B = phase_b(audit_b)
    finally:
        if proc is not None and not a.keep_sitl:
            import signal
            try:
                os.killpg(proc.pid, signal.SIGTERM)  # whole session (dronekit-sitl spawns apm child)
                proc.wait(10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    capA, capB = A["capture"], B["wire"]
    tx_names = set(capA.get("tx_counts", {})) | set(capB.get("tx_counts", {}))
    cmds_on_wire = {t.get("command") for t in capA.get("tx", []) + capB.get("tx", []) if t.get("msg") == "COMMAND_LONG"}
    acks = capA.get("command_acks", [])
    ev_a_full = [json.loads(l) for l in audit_a.read_text().splitlines()] if audit_a.is_file() else []
    ev_a = [e["event"] for e in ev_a_full]
    ev_b = [json.loads(l) for l in audit_b.read_text().splitlines()] if audit_b.is_file() else []
    disp = A["displayed_counts"]
    criteria = {
        "connect_real_sitl_and_rx_heartbeat": bool(capA.get("vehicle_heartbeat")) and disp["HEARTBEAT"] > 0,
        "rx_telemetry_beyond_heartbeat": all(disp[k] > 0 for k in ("SYS_STATUS", "GLOBAL_POSITION_INT", "ATTITUDE", "BATTERY_STATUS")),
        "global_position_valid_near_home": bool(A["last_global_position"]) and "lat=-35.36" in A["last_global_position"] and "lon=149.16" in A["last_global_position"],
        "stream_setup_only_511_512": cmds_on_wire == {511, 512},
        "stream_cmds_acked_accepted": len(acks) >= 10 and all(x["result"] == 0 for x in acks) and {x["command"] for x in acks} == {511, 512},
        "tx_wire_subset_of_allowlist": tx_names <= {"HEARTBEAT", "COMMAND_LONG", "PARAM_REQUEST_LIST"},
        "no_locked_or_write_msgs_on_wire": not (tx_names & LOCKED_WIRE),
        "no_forbidden_commands_on_wire": not (cmds_on_wire & FORBIDDEN_CMDS),
        "all_negative_attempts_refused": all(v.startswith("refused") for v in B["refused"].values()),
        "refuse_events_audited": sum(1 for e in ev_b if e["event"] == "refuse") >= len(B["refused"]) + 1,
        "heartbeat_exempt_on_real_link": capB.get("tx_counts", {}).get("HEARTBEAT", 0) >= 5 and B["read_with_empty_bucket"].startswith("rate-limited"),
        "vehicle_remained_disarmed": B["vehicle_heartbeats_after"] > 0 and not B["vehicle_armed_seen"],
        "mavlink2_framing": set(capA.get("tx_frame_magic", {})) == {"mavlink2_0xFD"},
        "audit_minimum_includes_written": {"session", "scope_grant", "egress_opt_in", "revocation_check"} <= set(ev_a),
        # A1: in-process verify reports verified_local_key / verified_sigstore (cosign CLI = "verified")
        "revocation_check_ran_cosign_verified": bool(A["revocation_line"]) and A["revocation_line"].startswith("revocation check: ok (cosign=verified"),
        # N3: evidence run must not use dev-only flags; no skip outcomes in audit
        "no_dev_only_flags_n3": not ({"--skip-revoke", "--no-interval-check"} & set(A["cmd"])) and not any(
            e.get("outcome") in ("skipped_dev", "interval_skipped_dev") or e.get("dev_mode") for e in ev_a_full),
        "observer_exit_0": A["returncode"] == 0,
    }
    met = all(criteria.values())
    result = {
        "phase": "Phase 2", "draft": True, "mode": "REAL_SITL", "started_utc": started,
        "sitl": info, "connection": CONN, "criteria": criteria, "all_criteria_met": met,
        "phase_a": {k: v for k, v in A.items() if k != "capture"} | {
            "tx_counts": capA.get("tx_counts"), "tx_frame_magic": capA.get("tx_frame_magic"),
            "rx_types": capA.get("rx_types"), "rx_dropped_by_filter": capA.get("rx_dropped_by_filter"),
            "command_acks": acks, "vehicle_heartbeat": capA.get("vehicle_heartbeat"), "audit_events": ev_a},
        "phase_b": {k: v for k, v in B.items() if k != "wire"} | {
            "tx_counts": capB.get("tx_counts"), "audit_events": [e["event"] for e in ev_b]},
        "not_a_fake_peer": True,
    }
    (EVID / "e8-real-sitl-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["criteria"], indent=2))
    print("REAL SITL criteria met" if met else "REAL SITL criteria NOT met")
    return 0 if met else 1


if __name__ == "__main__":
    raise SystemExit(main())
