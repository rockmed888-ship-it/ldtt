"""N1: --heartbeat-hz must be <= 2."""

from ldtt_ref_mav_observer.__main__ import HEARTBEAT_HZ_MAX, main


def test_heartbeat_hz_max_constant():
    assert HEARTBEAT_HZ_MAX == 2.0


def test_heartbeat_hz_over_cap_exits():
    rc = main(["--validate-only", "--heartbeat-hz", "2.5"])
    # argparse runs before validate-only body; cap check is first
    assert rc == 2


def test_heartbeat_hz_at_cap_ok_validate():
    # 2.0 is allowed; validate-only returns 0 if yaml valid
    rc = main(["--validate-only", "--heartbeat-hz", "2.0"])
    assert rc == 0
