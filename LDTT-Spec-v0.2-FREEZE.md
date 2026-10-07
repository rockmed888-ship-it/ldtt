# Spec v0.2 FREEZE note

**Frozen:** 2026-10-06 18:36 CDT (America/Chicago)  
**Publish-ready:** 2026-10-07 09:16 CDT  
**Lead GO (freeze):** creator · **Lead OK (publish Spec + FREEZE):** creator → Open Builder  
**Owner:** LDTT Spec Writer  
**Scope:** Phase 1 Spec v0.2 at draft **r5.1**  
**Push (this GO):** Spec + FREEZE note (+ STATUS). **No workflows.** Environments / rulesets **not** touched.

## Published / to-publish artifacts (repo-relative)

| Path | Role |
|---|---|
| `LDTT-Stamp-Spec-v0.2.md` | Frozen Phase 1 Spec v0.2 (from draft sections r5.1) |
| `LDTT-Spec-v0.2-FREEZE.md` | This note |
| `LDTT-Spec-v0.2-STATUS.md` | STATUS + Open Builder push allowlist |

Box working copies of the draft history remain under `drafts/` (not required for this push).

## Corrector PASS refs

| Rev | Verdict | Review (box; optional publish) |
|---|---|---|
| r4 | **PASS** | `reviews/LDTT-Spec-v0.2-r4-corrector-delta.md` |
| r5 | **PASS** | `reviews/LDTT-Spec-v0.2-r5-corrector-delta.md` |
| r5.1 | N32 hygiene only (reorder §F.3 before §F.4); no Corrector re-skim required | change log in Spec |

Prior CONDITIONAL rounds (r1→r3) and FOLD1/FOLD2/N29–N31 are in the Spec change log.

## Still open (not blockers for this freeze / this publish)

- **Q-B1** (user): can BlueOS install an extension pinned by image digest?
- **Q-A3:** offline Sigstore trusted-root cache / refresh
- **Q-A4** (Lead lean, not frozen): branch rules / ruleset bypass for publish path; Environment `ldtt-issuer` still Lead-created
- **Q-D1:** Observe stream-rate changes while another GCS is connected
- **Q-Q11:** confirm `connector.package_version` vs relaxing `version` pattern

**Lead leans recorded but not freeze-locked:** Q-A2 → GitHub Actions + Sigstore keyless only for v0.2.

## Explicitly pending (post-freeze; HOLD for later GOs)

- `schema/ldtt.schema.json` **0.2.0** file not written yet (delta table only in Spec §F.1 / §F.1.1)
- Signing workflows (`.github/workflows/ldtt-issue.yml`, `ldtt-revoke.yml`) remain **box drafts** until workflow-scope device-code + Lead GO
- Environments / rulesets remain Lead-owned
- **[N31]** PLAN REF: reference checkers need v0.2 conformance before any v0.2 stamp (Open Builder later)

## Non-goals reminder

LDTT is a connector stamp only: not aircraft certification, not a fleet dashboard, no FAA or airworthiness claims.
