# Corrector review: LDTT Stamp Spec v0.1
Date: 2026-10-06 · Reviewer: LDTT Corrector · File: /workspace/ldtt/LDTT-Stamp-Spec-v0.1.md

## Verdict: FAIL (minor, quick re-review)
Clean on brand (Linked Drone Tool Trust throughout), connector-only scope, no FAA/aircraft claims, phase order, and $0 tooling. Fails exit criterion 1 on two coherence drifts (D1, D2). Everything else is a small FIX or PLAN REF.

## DRIFT
- D1 (levels vs non-goal 4): Operate allows "parameters" and "geofences" writes. That lets an Operate connector disable failsafes, fences, arming checks, or Remote ID through params (e.g. FENCE_ENABLE, FS_*, ARMING_CHECK), contradicting non-goal 4 "not replace or override autopilot failsafes, geofencing, or Remote ID". FIX: operate:params must declare a param allowlist; failsafe, fence-enable, arming-check, and Remote ID params are not stampable at any level in v0.1. operate:geofence may edit a fence but not disable it.
- D2 (C4 fail-closed vs offline field use): "fails closed" doesn't distinguish "revoked" from "revocation status unreachable". Read literally, an offline Operate/Command connector bricks in the field. FIX: revoked = must stop writes/commands; unreachable = use last-known signed list up to a declared max staleness (new manifest field, e.g. max_staleness_s), then fail closed. Also define Observe behavior when revoked (stop egress and warn, or refuse to start).

## FIX
- F1 Manifest `message_allowlist` is ambiguous (example lists messages the connector receives, but E8 checks what it sends). Split into `rx_allowlist` and `tx_allowlist`.
- F2 `command_allowlist`: state that at Operate it may only hold non-motion MAV_CMDs (camera/payload), and flight-state MAV_CMDs only at Command.
- F3 Example Observe manifest sets `commands_per_min: 6` and `writes_per_min: 10`. At Observe these must be 0 or omitted.
- F4 The stamp record itself is undefined (§1 says "signed record" but no fields). C4 depends on it. Add a minimal format: connector_id, version, artifact_digest, level, scopes, known_limitations, issuer, issued_at, expires_at, signature. Same for the revocation list (entries + issued_at + signature).
- F5 Non-goal 5 names HALO in a public spec, which keeps the old brand alive. Reword to "LDTT is not a rebrand or successor of any prior program" without naming it.
- F6 (optional) `pii: false` beside `collects: vehicle_location` is misleading; location near an operator is personal data. Replace boolean with "personal data categories" or drop it.
- F7 (optional) E12 replay/stale-session notes should also apply to Operate, since writes can be replayed too.

## PLAN REF
- P1 MAV_CMD/message to scope mapping table: hand to Phase 2 (Open Builder) as part of the reference connector, fold into v0.2.
- P2 Batch approval for Operate writes (e.g. one confirmation for a 50-waypoint mission upload) is implied but not stated. Fine for v0.1; clarify in v0.2.
- P3 "LDTT reviewers" are unnamed. Resolve with Q1 below.

## Recommended answers to §8
1. Issuer/hosting: the LDTT project issues stamps in v0.1. Stamps and the revocation list are signed files in a public repo (Sigstore/cosign, keyless or a project key held by creator), served from the repo or free static hosting. $0. Revocation list carries issued_at so connectors can apply max staleness (D2).
2. Observe with egress: stamp it, no new level. Egress must be declared, off by default, turned on by the operator at runtime, destinations listed, retention stated, encrypted in transit. The stamp shows an "egress" flag. Undeclared egress = no stamp.
3. Transport: in v0.1, stamp the vehicle link. Any connector whose vehicle side is MAVLink 2 is in scope, whatever its front end (MCP, HTTP, stdio), which keeps AI-agent tool connectors in from day one. MCP front ends must list exposed tools mapped to scopes (add a `tools:` block). Pure vendor-API connectors with no MAVLink go to v0.2.
4. Expiry: yes, max 12 months on top of per-version binding; renewal = rerun the E checks (free). Expiry is a registry status, not a runtime kill switch; only revocation stops a connector at runtime.
