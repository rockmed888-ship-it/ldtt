# Corrector notes: Spec v0.1.4 quick-pass + Phase 2 ARCHITECTURE.md §7 skim
Date: 2026-10-06 · Reviewer: LDTT Corrector

## Spec v0.1.4 (schema-only patch): PASS
- test_schema.py passes 67/67. The v0.1.1 and v0.1.2 probes give the same results as at the v0.1.3 PASS (only the expected-valid cases validate).
- Diff from v0.1.3 is S1 only: list_url may be https://, file:, or a relative path, with signature + list_version + max_staleness rules unchanged. http:// and absolute paths are still rejected. Levels, controls and non-goals are unchanged.
- Cosmetic, non-blocking: the §5 stamp/revocation examples say ldtt_spec "0.1.3"; the template is still v0.1.3. Both are fine because the schema accepts 0.1.3 and 0.1.4.

## ARCHITECTURE.md §7 vs frozen spec: FAIL on one note (draft, cheap fix)
- A1 (§7 #1, §4 step 4, ldtt.yaml known_limitations C4): when cosign is missing, Observe "fails open" and loads the revocation list unsigned. That contradicts C4 ("signed revocation list") and the v0.1.4 rule "wherever it's loaded from, the list must pass cosign signature verification". known_limitations states limits plainly but doesn't waive a frozen control.
  Fix (no behavior loss): treat "cosign missing" like "list unreachable". Keep the last verified list until max_staleness_s, then apply Observe's fail-closed behavior (warn + stop egress; for this no-egress observer that's just a warning). Never load an unsigned list. Or verify the Sigstore bundle in-process with sigstore-python (Apache-2.0, free) so there's no external-binary dependency. Then drop the C4 known_limitation.

## Non-blocking
- N1 (C6): HEARTBEAT TX is exempt from reads_per_s, and --heartbeat-hz is user-set and unbounded. Cap it (e.g. ≤ 2 Hz) or declare it in rate_limits so "must not flood the link" still holds.
- N2: With v0.1.4 passed, ldtt.yaml can point list_url at the relative placeholder path for local DoD and drop the --revocation-list override comment; swap to https when the public repo exists.
- Everything else in §7 matches the freeze: REQUEST_DATA_STREAM and LOG_REQUEST_* removed, F8 stream setup, audit includes as a minimum set, P4 Command-now/protect-v0.2, no Operate tx widening, protected list widened in draft only, LGPL pymavlink documented. ldtt.yaml validates.

## A1 re-check (Open Builder fix, 41 tests): FAIL on A1-r (one narrow item)
Fixed: the fetch path never applies an unverified list. A failed verify or missing cosign goes through _on_unreachable (last verified list until max_staleness_s, then fail closed; no list at all = fail closed). The C4 known_limitation is gone. There's in-process verify (local key / sigstore-python) with the CLI as an optional fallback. Rollback is rejected. ldtt.yaml uses the relative list_url (N2 done). 41/41 tests pass.
- A1-r: RevocationChecker.load_cache() (called at startup in __main__.py:199) reads ~/.ldtt/cache/<id>.revocations.json and sets has_verified_list=True with no signature check, and skips the rollback check. If the list is unreachable at startup, that unsigned file drives C4. An edited issued_at would extend staleness indefinitely or hide a revocation. That contradicts "never load an unsigned list".
  Fix: save_cache writes the original body bytes (not json.dumps of the parsed copy, which changes the bytes and breaks the signature) plus the .sigstore.json bundle. load_cache re-runs verify_fn and ignores the cache if verification fails. Add a test where a tampered cache is ignored and the result is unreachable_no_cache / fail closed.

## A1-r re-check (45 tests): PASS
- save_cache writes the original verified body bytes plus the sibling .sigstore.json bundle, never a re-serialized copy.
- load_cache re-runs verify_fn and ignores a tampered/unsigned cache. It also runs the list_version rollback check and ignores a rolled-back cache. __main__ wires verify_fn before load_cache.
- No verified cache + unreachable/unverified list = unreachable_no_cache, fail closed.
- Tests cover all of these: test_save_cache_preserves_original_body_and_bundle, test_tampered_cache_ignored_unreachable_no_cache, test_load_cache_reverify_ok_then_unreachable_uses_cache, test_load_cache_rollback_ignored, test_unverified_never_loads_list_no_cache_fail_closed. 45/45 pass.

## Carry to Phase 2 freeze (outside this check)
- N3: --skip-revoke and --no-interval-check turn off C4 silently. Before the Phase 2 freeze: gate them behind a dev-only switch (e.g. LDTT_DEV=1) or strip them from release builds, audit-log revocation_check outcome "skipped" when used, and make sure E6 evidence comes from runs without them.

## N3 + E3 review (Phase 2 draft, 57 tests): PASS
N3: --skip-revoke / --no-interval-check need LDTT_DEV=1 exactly. Without it they're refused (exit 2, audited, no session). With it, every skip is audited (skipped_dev / interval_skipped_dev), and the session is marked dev_mode / evidence_eligible:false. The evidence checker runs in tests/CI. E6, E5 and E8 evidence contain no skip markers; older runs were moved to superseded-dev-flags/. 57/57 pass.
E3 (checked independently):
- wheel sha256 = 1c8c29db… matches SHA256SUMS and ldtt.yaml artifact_digest.
- The wheel signature verifies against placeholders/keys/ldtt-placeholder.pub, and a tampered wheel fails.
- The provenance DSSE envelope verifies against the same key. Its subject is the wheel digest, and its source is commit fe1e34e.
- fe1e34e exists publicly on github.com/rockmed888-ship-it/ldtt.
- The private key is gitignored and not in the public repo tree; it's an encrypted sigstore key on the box only.
- The C3 known_limitation honestly states placeholder key, local builder, CI keyless inactive.

## PLAN REF (before the Phase 2 freeze / first real stamp)
- P5: Turn on CI keyless signing + attest-build-provenance (the workflow has to live at repo-root .github/workflows/). CI should rebuild and check the digest. I didn't rebuild the wheel myself.
- P6: Trust root. The revocation list and wheel are verified with a placeholder key that sits on the shared box. Before any real stamp, move to the LDTT issuer key held by creator (§9.1), or a keyless issuer identity, and update the connector's verify config.
- P7: Canonical repo. An earlier draft referenced github.com/dustindent9-cmyk/ldtt; it's now rockmed888-ship-it/ldtt. Lock one, because source_url, provenance, list_url and any keyless identity all bind to it.
- Ops (not spec): re-sign revocations.json before ~2026-10-07 03:42 CT, or Observe fails closed (warns) on staleness.
