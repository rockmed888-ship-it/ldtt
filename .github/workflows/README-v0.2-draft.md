# LDTT workflows — Spec v0.2 r5.1 FROZEN box drafts

**Status:** BOX DRAFT ONLY. **DO NOT PUSH** to `rockmed888-ship-it/ldtt` until workflow-scope device-code OK and Lead GO.

**Spec source:** `drafts/LDTT-Spec-v0.2-draft-sections.md` (v0.2 **r5.1** FROZEN), especially §A.2, §A.2.1, §A.3 (publish path, FOLD2 concurrency, N28 self-verify, R2 `issued_at`).

**Corrector skim:** W1–W6 PASS vs r5.1 (2026-10-07); path-guard closed. See `reviews/LDTT-Spec-v0.2-r5.1-workflow-conformance.md`.

## Files in this directory

| File | Role | Push? |
|---|---|---|
| `ldtt-revoke.yml` | Revoke signing (keyless target shape) | **HOLD** |
| `ldtt-issue.yml` | Issuer signing (keyless; env gate) | **HOLD** |
| `ldtt-ref-mav-observer-ci.yml` | Phase 2 connector CI (already on box; style ref) | separate |
| `ldtt-ref-mavsdk-observer-ci.yml` | mavsdk CI box draft | **HOLD** (existing) |
| `README-v0.2-draft.md` | this note | **HOLD** |

Helpers (box `scripts/`):
- `scripts/ldtt_revoke_prepare.py` — §A.2.1 build/check + §A.3.6 time check (`--doc` for stamp/trust too)
- `scripts/ldtt_path_guard.py` — **W1** path-escape guard (stamps/ / trust/)
- `scripts/validate_revocation_list.py` — **W5** list schema/shape

## What Lead must create later (NOT done by Open Builder) — W6

- **Environment `ldtt-issuer` + required reviewer** must be created by Lead **before** Issuer runs (`ldtt-issue.yml` references `environment: ldtt-issuer`).
- **Q-A4 still open:** branch rules / ruleset bypass for the publish path (§A.3.4 Lead lean) — not frozen; not created here.
- **This draft does not create Environments or rulesets on the remote.**

## Spec checklist (both signing workflows)

- §A.2 pinned identities + OIDC issuer `https://token.actions.githubusercontent.com`
- §A.3.2 run only on `main`; **no** `pull_request` / `pull_request_target`; **W3** `if: github.ref == 'refs/heads/main'` on `sign-and-publish`
- §A.3.2 third-party actions pinned by **full commit SHA**:
  - `actions/checkout@11d5960a326750d5838078e36cf38b85af677262` (= v4.4.0)
  - `sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6` (= v4.1.2)
  - **W2** `actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02` (= v4.6.2)
- §A.3.4 only `sign-and-publish` has `id-token: write` + `contents: write`
- §A.3.4 [R2] `issued_at` inside gated job, immediately before sign
- §A.3.4 [N28] self-verify before commit; on fail do not commit; log Rekor + `workflow_sha`
- §A.3.4 [FOLD2] `concurrency: { group: ldtt-revocations, cancel-in-progress: false }`; fail if main moved
- §A.3.4 path-scoped commits; **W1** resolve+containment guard on stamp/trust (validate + pre-git-add)
- §A.3.6 time check (**W4**) for revoke lists and Issuer list/stamp/trust-root
- §A.3.9 Revoke schedule every 6h + `workflow_dispatch`
- §A.2.1 Revoke: base field + append-only; Issuer omits `base`, writes `revocations/base/*`

## Real vs draft

Until P6 (trust root live, Issuer base published, placeholder key retired), signatures from these workflows are the **target shape**. Placeholder-key re-signs (ops) remain draft and never count as real (§A.1). Revoke v6 prep remains **HOLD PUSH**.
