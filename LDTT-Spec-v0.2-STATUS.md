# Spec v0.2 — STATUS

**Status:** **FROZEN** (Phase 1 Spec v0.2 = draft r5.1)  
**Frozen:** 2026-10-06 18:36 CDT  
**Publish-ready:** 2026-10-07 09:16 CDT · Lead OK for Open Builder to push **Spec + FREEZE note only** (no workflows)  
**Owner:** LDTT Spec Writer · **Lead:** creator · **Publisher:** LDTT Open Builder  
**Canonical repo (P7):** `rockmed888-ship-it/ldtt`  
**$0** · box prep only from Spec Writer; Spec Writer does **not** push.

## Open Builder — push these (and only these) for this GO

| Repo path (on `main`) | Box source | Notes |
|---|---|---|
| `LDTT-Stamp-Spec-v0.2.md` | `/workspace/ldtt/LDTT-Stamp-Spec-v0.2.md` | Frozen Spec body (r5.1) |
| `LDTT-Spec-v0.2-FREEZE.md` | `/workspace/ldtt/LDTT-Spec-v0.2-FREEZE.md` | FREEZE note |
| `LDTT-Spec-v0.2-STATUS.md` | `/workspace/ldtt/LDTT-Spec-v0.2-STATUS.md` | This STATUS |

Optional (same freeze evidence; push only if Lead expands the GO):
| `reviews/LDTT-Spec-v0.2-r4-corrector-delta.md` | box same path | Corrector PASS r4 |
| `reviews/LDTT-Spec-v0.2-r5-corrector-delta.md` | box same path | Corrector PASS r5 |

## Do **not** push with this GO

- `.github/workflows/ldtt-issue.yml`, `ldtt-revoke.yml`, `README-v0.2-draft.md` (held for device-code / workflow scope)
- `schema/ldtt.schema.json` 0.2.0 (file **not written**; HOLD)
- Environments / rulesets (Lead-owned)
- Draft history under `drafts/LDTT-Spec-v0.2-draft-sections-r*.md`
- N31 checker work / open-Q resolutions (HOLD unless already frozen text)

## Integrity (box, before push)

| File | sha256 |
|---|---|
| `LDTT-Stamp-Spec-v0.2.md` | `f424aba526b1589734be9ea5d9626dd659188d74408fbecd98feaafae6983ebe` |
| *(recompute after any Spec Writer edit before push)* | |

## Still open (documented in Spec §E / FREEZE note; not blockers)

Q-B1 (user), Q-A3, Q-A4, Q-D1, Q-Q11. Q-A2 Lead lean recorded (GitHub Actions + Sigstore keyless only).
