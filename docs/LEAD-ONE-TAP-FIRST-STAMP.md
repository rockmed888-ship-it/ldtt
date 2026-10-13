# Lead one-tap — first real Observe stamp (P6)

**Why:** Phase 2 DoD #5 is the only Phase 2 fail. `revocations/base/*` is missing until `ldtt-issue` runs with **mode=revocation-list**, so the `ldtt-revoke` cron fails every schedule until then (expected).

**Do not:** fake a stamp, outreach, or claim certification.

## Your one tap now

**Approve the waiting `ldtt-issue` run** (mode=stamp, Observe `stamps/org.ldtt.ref-mav-observer/0.1.0.json`) as required reviewer on environment `ldtt-issuer`.

- Run: https://github.com/rockmed888-ship-it/ldtt/actions/runs/38412130870
- Env activity: https://github.com/rockmed888-ship-it/ldtt/deployments/activity_log?environments_filter=ldtt-issuer
- Account: `rockmed888-ship-it`

After that run succeeds: expect the keyless stamp (`stamps/org.ldtt.ref-mav-observer/0.1.0.json` + `.sigstore.json`) on main. **Correction (2026-10-13):** mode=stamp does **not** write `revocations/base/*`. Only `ldtt-issue` **mode=revocation-list** writes base (list + base, same bytes, Issuer-signed, no `base` field). The revoke cron keeps failing on missing base until that seed run (list_version 13) is approved.

**Status:** done — stamp run 38412130870 landed at `25a67be` (Rekor 3246036137). Next: seed base v13 (mode=revocation-list), then re-issue the stamp with the corrected C3 note.

## Already green (no action)

- Spec v0.2 Phase 1 PASS; Phase 2 FROZEN (draft stamp only until this run)
- `workflow` scope on box `gh` (rockmed888-ship-it)
- Commit `897a966` already on main (your Oct 8 author)
- Public revoke **list_version 11** @ `1cf5964` (issued 2026-10-13T13:17:10Z); next stale **Wed 2026-10-14 08:17 CT**
- `ldtt-ref-mav-observer-ci` green on latest revoke push
- `trust/trust-root.json` present but placeholder (`issued_at` epoch) — not a real stamp yet

## Box / bots until you tap

- Manual revoke refresh before Wed 08:17 CT if Issuer still blocked
- Site mock stays box-only; DNS/outreach HOLD
- No fake certification
