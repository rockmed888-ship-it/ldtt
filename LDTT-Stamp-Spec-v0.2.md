# LDTT Stamp Spec v0.2

> Phase 1 Spec v0.2 · frozen from draft sections r5.1 · Lead OK to publish Spec + FREEZE note (no workflows)

**LDTT = Linked Drone Tool Trust** · Phase 1 lane · **FROZEN 2026-10-06 18:36 CDT · publish-ready 2026-10-07 (Lead OK: Spec + FREEZE only; no workflows)** · Owner: LDTT Spec Writer · Lead: creator
**Frozen Spec:** `LDTT-Stamp-Spec-v0.2.md` · **FREEZE note:** `LDTT-Spec-v0.2-FREEZE.md` · **STATUS:** `LDTT-Spec-v0.2-STATUS.md`
Base: v0.1.4 (frozen levels, controls C1–C9, non-goals). Nothing here changes levels, controls, or non-goals (see §F). $0 throughout: free GitHub Actions on a public repo, the Sigstore public-good service (Fulcio + Rekor), and GitHub artifact attestations.
Canonical repo (P7, locked): `rockmed888-ship-it/ldtt`.

**Change log:**
- **FREEZE 2026-10-06 18:36 CDT:** Lead GO freezes Phase 1 Spec v0.2 at r5.1. See `LDTT-Spec-v0.2-FREEZE.md`.
- **PUBLISH-READY 2026-10-07 09:16 CDT:** Lead OK for Open Builder to push Spec + FREEZE (+ STATUS). No workflows. See `LDTT-Spec-v0.2-STATUS.md`.
- **r5.1** hygiene **[N32]**: reorder §F so §F.3 (`trust-root.json`) precedes §F.4 (PLAN REF). No other content changes.
- **r5** folds Corrector r4 PASS notes: workflow cross-link to box drafts, schema 0.2.0 behavior delta table vs 0.1.4, **[N30]**, **[N31]** PLAN REF, and Lead lean on Q-A2. No freeze, no push.
- **r4** applied FOLD 1, FOLD 2 (Q-C2) and N29. Tagged **[FOLD1]** / **[FOLD2]** / **[N29]**.
- **r3** applied R1–R3 and N24–N28, plus the Lead's Q-A4 lean. Tagged **[R#]** / **[N##]**.
- **r2** applied Corrector CONDITIONAL M1–M6 and S1–S7, tagged **[M#]** / **[S#]**.
- Earlier texts are kept for delta-check at `drafts/LDTT-Spec-v0.2-draft-sections-r{1,2,3,4}.md`.
- Corrector r4 PASS review: `reviews/LDTT-Spec-v0.2-r4-corrector-delta.md`.

---

## A. Trust root (P6): what must be true before any real stamp

### A.1 Rule
A stamp, trust root, or revocation list is **real** only if it is signed **keyless** (cosign + Sigstore) by one of the two LDTT signing workflows in the canonical repo (§A.2), each within its allowed scope, and verifies against that exact identity. Everything else is a draft. Signatures made with the placeholder key are labeled draft and never count as real.

### A.2 Pinned identities [M1] [S6]
All identities share the OIDC issuer `https://token.actions.githubusercontent.com`.

| Role | Workflow | May sign | May NOT sign | Gate |
|---|---|---|---|---|
| **Issuer** | `https://github.com/rockmed888-ship-it/ldtt/.github/workflows/ldtt-issue.yml@refs/heads/main` | stamp records; `trust/trust-root.json`; **any** revocation list, including one that **removes** entries | — | GitHub environment `ldtt-issuer` with the user as required reviewer (one click per run) |
| **Revoke** | `https://github.com/rockmed888-ship-it/ldtt/.github/workflows/ldtt-revoke.yml@refs/heads/main` | the revocation list **only**, and only as an append-only successor of the Issuer **base** (§A.2.1) | stamps, trust root, any list that removes entries | none (`schedule` + `workflow_dispatch`), so re-signing never waits for a click |
| **Artifact signer** (LDTT-built connectors) | `https://github.com/rockmed888-ship-it/ldtt/.github/workflows/<connector>-ci.yml@refs/heads/main` | release artifacts + build provenance | stamps, lists, trust root | branch rules (§A.3) |
| **Artifact signer** (third-party holder) | the holder's **GitHub Actions** release workflow, `…/.github/workflows/<file>.yml@refs/heads/main` (or a release tag ref the holder declares) | their own release artifacts + provenance | stamps, lists, trust root | the holder's own controls; declared in the manifest, recorded on the stamp. **Lead lean (Q-A2, not frozen):** GitHub Actions + Sigstore keyless only for v0.2 — no alternate private CA, no non-GitHub OIDC issuers |

**Verifier acceptance:**
- **Stamp verifiers** accept **only** the Issuer identity.
- **Revocation-list verifiers** accept **Revoke OR Issuer**. A list signed by Revoke must also pass the base and append-only checks in §A.2.1. If they fail, it is treated as **unreachable** (§C.3).
- **Trust-root verifiers** accept only the Issuer identity.
- Every check uses the exact identity string and OIDC issuer (`cosign verify-blob --certificate-identity … --certificate-oidc-issuer …`). Identity regexps aren't allowed for the Issuer or Revoke roles. Where the tool supports it, verifiers also check the certificate's workflow repository and ref claims.
- Both the Issuer and Revoke identities are listed in `trust-root.json` **and pinned in connector code/config** (the bootstrap; connectors never learn them from the network).

**Box workflow drafts (match this section; not pushed).** Prose here is the source of truth for roles and gates. The matching GitHub Actions files on this box are:
- `.github/workflows/ldtt-issue.yml` — Issuer; `environment: ldtt-issuer` with required reviewer.
- `.github/workflows/ldtt-revoke.yml` — Revoke; schedule + `workflow_dispatch`; no reviewer; append-only successor of the Issuer base.
- `.github/workflows/README-v0.2-draft.md` — checklist and Lead-owned setup notes.

**Lead-owned before Issuer runs (not created by Spec Writer or Open Builder):** the GitHub Environment `ldtt-issuer` with the user as required reviewer must exist on `rockmed888-ship-it/ldtt` before any real `ldtt-issue.yml` run. **Q-A4** (branch rules / ruleset bypass for the publish path, §A.3.4) stays open and not frozen. These workflows stay box drafts until Lead GO and the workflow-scope device-code path are ready.

#### A.2.1 Issuer base and Revoke-workflow constraints [M1] [R1]
**Base (Lead-locked, R1).** Every Issuer-signed revocation list is also published at a fixed path:
- `revocations/base/revocations.json`
- its Sigstore bundle, `revocations/base/revocations.json.sigstore.json`

That is the **base**. Only the Issuer workflow writes `revocations/base/*`.

**A Revoke-signed list must carry:**
```json
"base": {"list_version": <list_version of the current base>, "sha256": "<sha256 of the base file bytes>"}
```
An Issuer-signed list omits `base`.

1. **Enforced in `ldtt-revoke.yml` before signing:**
   - `base` points to the current file at `revocations/base/`.
   - `revoked[]` is a **superset** of the base's `revoked[]` **and** of the currently published list. Entries are never removed or edited.
   - `list_version = previous + 1`.
   - `issued_at` = the run time (UTC), generated immediately before signing.
   - `issuer` and `ldtt_spec` are unchanged.
   If any check fails, the workflow fails without signing.
2. **Enforced by connectors on every Revoke-signed list, including the first fetch (no "known limitation" fallback):**
   1. Fetch the base from `base/revocations.json` and `base/revocations.json.sigstore.json`, resolved relative to `list_url`.
   2. Verify the base under the **Issuer** identity only.
   3. Check that `sha256(base bytes) == base.sha256` and that the file's `list_version == base.list_version`.
   4. Check that the Revoke list's `revoked[]` is a superset of the base's `revoked[]` (entries identical).
   5. Check that the Revoke list's `list_version` is greater than `base.list_version`.
   6. If the last verified list carries the **same** `base.sha256`, the new list must also be a superset of it.
   7. **[FOLD1] Base floor.** Connectors persist the **highest verified base `list_version`**, together with its `sha256`, in the same cache as the last verified list (the reference connectors' A1-r cache). If the last verified list was **Issuer**-signed, its own `list_version` and sha256 set the floor. The Revoke list is **unreachable** if:
      - its `base.list_version` is **below** the floor, or
      - its `base.list_version` **equals** the floor but `base.sha256` differs.
      Optional: a connector release may also ship a build-time minimum base `list_version`, used as the floor when the cache is empty.
   If the base can't be fetched or fails any check, the Revoke list is **unreachable** (§C.3).
   **[N29]** `raw.githubusercontent.com` caches files briefly. A fetch can therefore see a new base next to a still-cached older list (so `base.sha256` won't match). That list is unreachable for that check, and the last verified list holds. It clears on a later fetch and is **not an incident**.
3. **Removals move the base on purpose.** An un-revoke or correction needs the **Issuer** workflow, so it always gets the user's click. That Issuer list becomes the new base. Later Revoke lists point to it, and connectors then compare against the new base instead of the older Revoke list.
4. Issuer-signed lists follow the normal v0.1.4 rules: monotonic `list_version` and the staleness rules in §C.

### A.3 Preconditions (all must hold before the first real stamp)
1. **P7 locked:** the canonical repo is the only source for `source_url`, `list_url`, provenance, and identities. Done.
2. **Both signing workflows exist** at the repo root, run only on `main`, never on `pull_request` or `pull_request_target`, and pin third-party actions by full commit SHA.
3. **Account and branch hygiene:**
   - 2FA is on for the repo owner account.
   - Force-push and deletion are blocked on `main`.
   - Workflow files change only through commits on `main`. Changing an identity means a new trust-root release, never a silent edit.
4. **Publish path [M2]** (applies to both workflows):
   - Only the single **sign-and-publish** job gets `id-token: write` and `contents: write`. Every other job is read-only.
   - **[R2]** `issued_at` for lists, stamps and trust root is generated **inside** the gated sign-and-publish job, **after** environment approval, **immediately before** signing. It is never carried in from an earlier job, a PR, or the approval request. With that, the §A.3.6 tolerances (+300 s / 3600 s) hold.
   - **[N28]** Before committing, the job **self-verifies its output the way a connector would**, not just with cosign:
     - `cosign verify-blob` against its pinned identity.
     - Schema validation.
     - `list_version` monotonicity.
     - For Revoke lists, the base and append-only checks in §A.2.1.
     - The §A.3.6 time check against the bundle's Rekor time.
   - **[N28]** If signing succeeded (so a Rekor entry exists) but self-verify fails, the job **does not commit**. It records the Rekor log index, entry UUID, `workflow_sha` and failure reason in the run summary and in an append-only `revocations/selfverify-failures.log` (or the run artifact, if committing is unsafe), so §A.3.10 monitoring can explain that entry instead of flagging an incident.
   - **[FOLD2] Serialization:**
     - Both `ldtt-issue.yml` and `ldtt-revoke.yml` use the shared `concurrency: { group: ldtt-revocations, cancel-in-progress: false }`, so only one list is computed and published at a time.
     - If `main` has moved since the job read the published list (the push is rejected as non-fast-forward), the publish **fails**. There is no rebase, no retry, and no re-push of the same `list_version`.
     - A rerun recomputes the list, `list_version` and `issued_at` from the new `main` and signs again. Any signed-but-unpublished entry is logged per [N28].
   - It commits **only its own paths**:
     - Revoke: only `revocations/revocations.json`, its bundle, and the self-verify log.
     - Issuer: only `stamps/*`, `trust/*`, `revocations/revocations.json`, `revocations/base/*`, and their bundles.
     Any other changed path fails the job.
   - Branch rules must **allow this commit**. Prefer a ruleset bypass for the publish workflows if the account tier allows one. **Lead lean (Q-A4, not frozen):** for a single-owner, $0 repo, dropping "require pull request" on `main` is acceptable, provided force-push and deletion are blocked, publishing is path-scoped as above, and §A.3.10 monitoring runs.
   - The commit message records `workflow_sha` and `list_version` (or the stamp id).
   - **Scheduled Revoke commits keep the repo active.** That avoids GitHub's rule that scheduled workflows in public repos are disabled after 60 days without activity. A manual `workflow_dispatch` path must still always work.
5. **Trust root file published:** `trust/trust-root.json`, signed by Issuer. Format in §F.3.
6. **Transparency log:**
   - Every real signature has a Rekor entry inside its bundle.
   - Verification must succeed **offline from the bundle**, against a cached Sigstore trusted root (Q-A3).
   - **[S1]** The verifier also checks the signed `issued_at` against the bundle's Rekor integrated time. It rejects the document if `issued_at` is more than 300 s **after** the integrated time (future-dated), or more than 3600 s **before** it (backdated, or held then signed). Staleness is still counted from `issued_at`. Tolerances accepted by Lead (Q-A5): +300 s / 3600 s.
7. **Provenance (with P5):** CI rebuilds the artifact, checks that the digest equals `build.artifact_digest`, signs it keylessly, and emits SLSA build provenance via GitHub attestations. The provenance subject digest(s) must match §B.
8. **Placeholder key retired:**
   - The placeholder public key is removed from every non-dev verify path.
   - Existing draft stamps are re-issued, not re-labeled.
   - Anything still verifying only with the placeholder key keeps a C3 `known_limitations` entry and stays draft.
9. **Re-sign cadence:** Revoke re-signs on a schedule well inside the shortest accepted `max_staleness_s`, for example every 6 h for 86400 s. Staleness alerts stay on.
10. **Identity monitoring [S4]:**
    - A scheduled job (free, e.g. the open-source Sigstore `rekor-monitor`, or a Rekor search by identity) lists every Rekor entry for the Issuer and Revoke identities.
    - Each entry's `workflow_sha` must match a commit on `main` **and** either a publish commit from §A.3.4 or a logged self-verify failure (**[N28]**).
    - An unexplained entry is an incident and triggers §A.5.

### A.4 Stamp record additions (v0.2) [S6]
```json
"signer": {
  "oidc_issuer": "https://token.actions.githubusercontent.com",
  "identity": "https://github.com/rockmed888-ship-it/ldtt/.github/workflows/ldtt-issue.yml@refs/heads/main",
  "workflow_sha": "<commit sha of the issuing run>"
},
"artifact_signer": {
  "oidc_issuer": "https://token.actions.githubusercontent.com",
  "identity": "https://github.com/<holder>/<repo>/.github/workflows/<file>.yml@refs/heads/main"
},
"dependency_lock_digest": "sha256:<…>"
```
`artifact_signer` replaces r1's `artifact_signer_identity`. `dependency_lock_digest` is defined in §B.3, and the required/optional rules are in §F.1.

### A.5 Compromise handling [M3]
- **Worst-case revoke latency.** If a connector can fetch the list, a revocation reaches it within `check_interval_s`. If the fetch is **blocked**, the worst case is **`max_staleness_s`**, counted from the last verified list's `issued_at`. At that point the connector fails closed. Holders and operators must size `max_staleness_s` with this in mind.
- **Order of operations** if Issuer or Revoke is suspected compromised (e.g. an owner-account takeover):
  1. **Recover** the account: rotate credentials, re-check 2FA, review workflow files and branch rules, and disable the affected workflow until it's clean.
  2. **Sign a revoking list with the OLD Issuer identity** (via the reviewer gate). It revokes every stamp issued in the suspect window. Current connectors still trust the old identity, so they can act on this list.
  3. **Then rotate:** create a new workflow path (a new identity), publish a new `trust-root.json` signed by the new Issuer, and ship connector releases with the new identities pinned.
- **Fleet effect, stated plainly [N24]:** connectors still pinned to the old identities **cannot verify** anything signed by the new identity. Once the old identity stops publishing, their last verified list goes stale, and v0.1.4 C4 applies unchanged. Verbatim:
  > **If revoked:** Operate/Command stop all writes and commands; Observe stops all egress and warns the operator. **If the list is unreachable:** keep using the last valid signed list until it is older than `max_staleness_s` (measured from the list's `issued_at`), then fail closed (same behavior as revoked).

  **[FOLD1] Residual, stated plainly:** a connector with **no cache**, on its first fetch with no build-time floor, cannot tell that a replayed **older** genuine Issuer base is not the latest. Serving such a replay at the canonical `list_url` needs a push to `main`, which is a §A.5 incident caught by §A.3.10 monitoring. Exposure is bounded by the Revoke list's own staleness (`max_staleness_s` from its `issued_at`), and it ends at the next fetch after the cache holds a newer floor.

  The LDTT reference connectors go further: on fail closed they halt the **whole session, TX and RX** (mavsdk-observer F1 + F5a). This is intended (fail closed over silent trust), but it's an operator-visible outage for every not-yet-updated connector until connectors are updated.

---

## B. Digest rule for containers and compiled plugins (P8)

### B.1 Principle
`build.artifact_digest` is the SHA-256 of **exactly what the operator installs or runs**, in the form its distribution channel can address and verify. Mutable names (tags, "latest", branch builds) are never bound. *(Lead confirmed: install digests, not tags.)*

### B.2 Rules by artifact type (`build.artifact_type`)

| `artifact_type` | What `artifact_digest` is (the **binding digest**) | Extra fields | Install / verify rule |
|---|---|---|---|
| `wheel` (Python) | `sha256` of the wheel file | `build.dependency_lock_digest` (§B.3) | §B.3 |
| `file` (single binary or archive) | `sha256` of the file bytes | none | install that exact file and check its sha256 |
| `oci-image`, single platform | the **image manifest digest** (the `sha256:` in `image@sha256:…`) | `build.oci.repository` | pull **by digest only**; cosign signature on `repository@digest`; provenance subject = that digest **[S3]** |
| `oci-image`, multi-platform | the **image index digest** | `build.oci.repository`, `build.oci.platforms[]` = `{platform, manifest_digest}` | pull by index digest; cosign signature on the index digest; **[S3]** provenance subjects must include **every** listed `manifest_digest`; the verifier checks that the platform manifest it actually resolves is in `platforms[]` **and** in the provenance subjects; unlisted platforms are not covered. **[N26]** Index entries that are attestation manifests or have an `unknown/unknown` (or other unknown) platform are **never** listed in `platforms[]` and **never** run |
| `plugin-binary` (`.so` / `.dll` / `.dylib` loaded by a host app) | `sha256` of the release **`SHA256SUMS`** file | `build.artifacts[]` = `{platform, filename, digest}`, `host` = `{name, version_range}` | §B.4 |
| compiled into the host (no separable file) | **not stampable in v0.2** | — | stays BLOCKED *(Lead confirmed)* |

### B.3 Dependency lock (required for `wheel`) [M5]
- The stamp **and** manifest carry `dependency_lock_digest`: the sha256 of a hash-locked requirements file (`ldtt.lock.txt`). The lock lists **every** runtime package with `--hash=sha256:…`, **including the connector wheel itself**. Its wheel hash must equal `artifact_digest`.
- **Install = `pip install --require-hashes -r ldtt.lock.txt`.** Nothing is installed outside the lock.
- **Evidence E4 and E8 run against an environment installed from that lock**, and the evidence records the lock digest.
- **Changing the lock means a new `connector.version`, a new stamp, and re-evidence.** Pinned native runtime dependencies (e.g. the `mavsdk` 4.x wheel with its **bundled native library `libcmavsdk.so`**, the Q9 pattern) **[N25]** are covered this way, and are also listed in the SBOM (C1).
- For `oci-image`, dependencies are inside the image digest, so there's no lock field. For `plugin-binary`, separately shipped native libraries are listed in `build.artifacts[]`, or else declared in `known_limitations` as host-provided.
- The stamp binding stays `connector_id + version + artifact_digest`. The lock digest is an extra required check for wheels, not part of the binding.

### B.4 Plugin verify rule and `SHA256SUMS` format [S2]
**Format:**
- One line per file: `<64 lowercase hex>` + two spaces + `<filename>` + LF. This is GNU `sha256sum` text-mode output.
- UTF-8, bare filenames (no paths), sorted by byte order, a trailing LF on the last line, and nothing else (no comments, no blank lines).
- Every entry in `build.artifacts[]` appears exactly once, and the file has no extra lines.

**Verification:**
1. Verify the cosign bundle on `SHA256SUMS` against the declared `artifact_signer`.
2. Check that `sha256(SHA256SUMS)` equals `artifact_digest`.
3. Pick the `build.artifacts[]` entry for the running platform. If there's none, the plugin is not covered and must not be loaded as stamped.
4. Check that `sha256(installed file)` equals both that entry's `digest` and its `SHA256SUMS` line, and that the filename matches.
5. The host app version must fall within `host.version_range`. The host itself is **not** covered by the stamp.

### B.5 Effect on beachhead
- **BlueOS extension (C2-4):** **may unblock pending Q-B1**, under the `oci-image` rules, if LDTT publishes its own image and BlueOS can install it pinned by digest. Not verified.
- **PlotJuggler plugin (C2-5):** unblocks only if a separable plugin file exists. If it's compiled into the host, it stays BLOCKED.

---

## C. Revocation entries and list handling (N7) [M6]
*Lead confirmed the N7 rule as recommended, plus M6.*

### C.1 Entry shape
- Each `revoked[]` entry **must** have `connector_id` (string) and `version` (string; `"*"` = all versions).
- `entry.version` is compared to the stamp's **`connector.version` (semver)**, never to `connector.package_version`.
- `digest` is **optional**. If present, it is the **binding digest from §B.2** for that artifact type: wheel or file digest, OCI manifest or **index** digest, or the `SHA256SUMS` digest. It is never a per-platform manifest digest or a single plugin-file digest. It narrows the entry to that exact build. If absent, the entry covers every build of that version.
- **Digest-only entries aren't allowed.**

### C.2 Match rule
`stamp.connector_id == entry.connector_id` AND (`entry.version == "*"` OR `entry.version == stamp.version`) AND (no `entry.digest` OR `entry.digest == stamp.artifact_digest`).

### C.3 Invalid list = unreachable
A list counts as unreachable if any of these hold:
- A malformed entry.
- A schema failure.
- A signature or identity failure.
- A failed Revoke base or append-only check (§A.2.1), including a base that can't be fetched.
- A failed §A.3.6 time check.

An unreachable list is **never applied, even partly, and never replaces the last verified list**. The last verified list stays in effect until `max_staleness_s` from its `issued_at`. After that the connector fails closed (C4).

### C.4 Rollback = fail closed immediately [R3]
*Lead pick (a): keep v0.1.4.* A signed list whose `list_version` is **lower than the last verified one** is a rollback. v0.1.4 §5.2: "A connector rejects any list with a lower `list_version` than the last one it accepted (no rollback)." The connector **fails closed immediately**, with the same behavior as revoked (C4 unchanged; E6 "rollback rejected"). Rollback is **not** handled through the unreachable/staleness path.
**[FOLD2] (Q-C2, Lead-locked):** a list with the **same** `list_version` as the last verified one but a **different body sha256** is also a rollback, so the connector fails closed immediately. Identical bytes are a normal re-fetch.

---

## D. Parked for v0.2

### P12: Observe stream-rate bounds [S5] *(Lead confirmed 100000 µs, no disable)*
Text matches the mavsdk-observer F2 gate:
- At Observe, `MAV_CMD_REQUEST_MESSAGE` and `MAV_CMD_SET_MESSAGE_INTERVAL` param1 must be finite, integral, and the id of a message in `rx_allowlist`.
- `SET_MESSAGE_INTERVAL` param2:
  - **`0` (default rate) is allowed.**
  - **`>= observe_limits.min_interval_us` is allowed.**
  - **`-1` (disable stream) is refused.**
  - **NaN and ±inf are refused.**
  - Any other value below the floor is refused.
- Every refusal is audited.
- `observe_limits.min_interval_us` is optional, with schema `minimum: 100000` (10 Hz). A holder may declare a slower floor, never a faster one. Default 100000.
- **[N27]** The floor is **enforced at Observe**. At Operate and Command it's **informational** unless this spec says otherwise.
- `REQUEST_MESSAGE` param2 is not bound.
- The schema can't see wire values, so this is enforced at runtime and evidenced in E8.
- **Q-D1 stays open:** whether Observe may change stream rates at all while another ground station is connected.

### Q11: Version string mapping
- `connector.version` stays semver, because it's the stamp binding and what revocation matches on (§C.1).
- New optional `connector.package_version` holds the ecosystem-native string (e.g. PEP 440 `0.0.1.dev0`). Verifiers compare it to the installed package.
- Until schema 0.2.0 ships, the documented mapping stands: manifest `0.0.1-dev0` ↔ wheel `0.0.1.dev0`.

### P11-spec (publisher_type), already adopted [S7]
`publisher_type` + optional Org Deployment Profile overlay. No new level, no evidence split, and no "verified org" display before §A is met.
**Erratum:** "P11" was used for two different things. **P11-spec** is this publisher_type item. **PLAN REF P11** in `ref-connectors/ldtt-ref-mavsdk-observer/STATUS.md` is the Phase 2 0.1.1 backport of F1 + F2. They're unrelated, and this draft uses "P11-spec" from now on.

---

## F. Schema delta and controls check [M4]

### F.1 Schema bump
`schema/ldtt.schema.json` → **schema 0.2.0**. `ldtt_spec` enum adds `"0.2.0"`, and `"0.1.3"` / `"0.1.4"` documents keep validating under their old rules. Not applied to the schema file yet (box draft; the schema change follows the freeze decision).

**Manifest (`ldtt.yaml`) fields.** R = required, O = optional, — = not allowed.

| Field | wheel | file | oci-image (1 platform) | oci-image (multi) | plugin-binary | Notes |
|---|---|---|---|---|---|---|
| `build.artifact_type` | R | R | R | R | R | enum `wheel`, `file`, `oci-image`, `plugin-binary` |
| `build.artifact_digest` (existing) | R | R | R (manifest digest) | R (index digest) | R (`SHA256SUMS` digest) | §B.2 binding digest |
| `build.dependency_lock_digest` | **R** | O | — | — | O | §B.3 |
| `build.oci.repository` | — | — | R | R | — | registry/repo, no tag |
| `build.oci.platforms[]` `{platform, manifest_digest}` | — | — | O | **R** (min 1) | — | §B.2 [S3] |
| `build.artifacts[]` `{platform, filename, digest}` | — | — | — | — | **R** (min 1) | §B.4 |
| `host` `{name, version_range}` | — | — | — | — | **R** | host not covered |
| `build.artifact_signer` `{identity, oidc_issuer}` | R | R | R | R | R | for LDTT-built connectors, the canonical CI identity |
| `observe_limits.min_interval_us` | O | O | O | O | O | integer, `minimum: 100000`; enforced at Observe, informational at Operate/Command **[N27]** |
| `connector.package_version` | O | O | O | O | O | ecosystem-native string; never a binding |

**Stamp record fields:**

| Field | Required | Notes |
|---|---|---|
| `signer.oidc_issuer`, `signer.identity`, `signer.workflow_sha` | R for real stamps | identity must equal the pinned Issuer identity |
| `artifact_signer.identity`, `artifact_signer.oidc_issuer` | R | copied from the manifest |
| `dependency_lock_digest` | R when `artifact_type = wheel`, otherwise as in the manifest | §B.3 |
| `artifact_type` | R | copied from the manifest |
| `expires_at` | still reserved, must be omitted | unchanged from v0.1 |

**Revocation list:**
- New field `base` `{list_version, sha256}` **[R1]**: **required** when the list is signed by Revoke, **omitted** when signed by Issuer.
- Schema-level, `base` is optional. The required-by-signer rule is a verifier rule, because the schema can't see who signed the list.
- New published path `revocations/base/` (Issuer-only).
- New rules: §A.2.1 base and append-only, §A.3.6 time check, §C.1 digest meaning, §C.3 invalid = unreachable, §C.4 rollback = immediate fail closed (unchanged from v0.1.4), plus **Q-C2**: the same `list_version` with a different body sha256 is a rollback **[FOLD2]**; §A.2.1 step 7 base floor **[FOLD1]**; shared `ldtt-revocations` concurrency with no same-version retry (§A.3.4) **[FOLD2]**.

### F.1.1 Behavior delta vs v0.1.4 (schema 0.2.0)
Field and verifier-behavior changes only. Levels, C1–C9 identities, and non-goals are unchanged.

| Topic | v0.1.4 | v0.2 (this draft) | Spec § |
|---|---|---|---|
| Trust root / signing | Placeholder-key drafts; no pinned Issuer/Revoke split | Keyless Issuer (`ldtt-issue.yml`, env `ldtt-issuer`) and Revoke (`ldtt-revoke.yml`); exact identity + OIDC issuer | §A |
| Stamp fields | No `signer` / `artifact_signer` / `artifact_type` / lock digest | New required fields per §F.1 tables | §A.4, §F.1 |
| `dependency_lock_digest` | — | Required for `wheel`; install = `pip install --require-hashes -r` lock; lock change = new version | §B.3 |
| Artifact digests (P8) | Wheel/file sha256 | + OCI manifest/index digests; plugin `SHA256SUMS` digest; compiled-into-host not stampable | §B |
| Revocation `base` | — | Required on Revoke-signed lists; Issuer omits; path `revocations/base/` | §A.2.1 |
| Base floor | — | Persist highest verified base `list_version`+sha256; below floor or same version≠sha256 → unreachable | §A.2.1 step 7 |
| N7 unreachable | Malformed / verify failure → keep last until `max_staleness_s`, then fail closed | Same C4 unreachable path; **never** replaces last verified; also covers failed base / append-only / S1 time | §C.3 |
| Rollback | Lower `list_version` than last verified → reject (fail closed) | Same, **plus Q-C2**: equal `list_version` with different body sha256 → fail closed immediately | §C.4 |
| Concurrency / publish | Not specified | Shared `ldtt-revocations` group; no same-version retry if `main` moved | §A.3.4 |
| `max_staleness_s` worst case | Measured from `issued_at`; fail closed when stale | Unchanged measure; **worst-case revoke latency when fetch blocked = `max_staleness_s`** (not `check_interval_s`) | §A.5 |
| `observe_limits.min_interval_us` | — | Optional; schema `minimum: 100000`; enforced at Observe | §D P12 |
| `connector.package_version` | — | Optional; never a binding; revocation matches `connector.version` | §D Q11, §C.1 |

Schema file `schema/ldtt.schema.json` is **not** updated on this pass (box draft; follows freeze).

### F.2 Controls C1–C9: unchanged
No control is added, removed, renamed, or re-leveled. v0.2 only makes them more precise:
- C1 (SBOM) gains the lock coverage in §B.3.
- C3 (signed builds) gains §A and §B.
- C4 (revoke) gains §A.2.1 and §C. Revoked and unreachable behavior match v0.1.4 C4 verbatim. Rollback still fails closed immediately as in v0.1.4 for a **lower** `list_version`. **[N30]** Q-C2 **tightens** rollback: the same `list_version` with a different body sha256 also fails closed immediately (§C.4).
- P12 is a runtime bound inside the existing Observe allowlist rules.
- C2 and C5–C9 are untouched.
Levels Observe, Operate and Command, and the non-goals, are unchanged.

### F.3 `trust/trust-root.json` (new file, signed by Issuer)
```json
{
  "ldtt_spec": "0.2.0",
  "trust_root_version": 1,
  "issued_at": "<UTC>",
  "identities": {
    "issuer": {"oidc_issuer": "https://token.actions.githubusercontent.com", "identity": "https://github.com/rockmed888-ship-it/ldtt/.github/workflows/ldtt-issue.yml@refs/heads/main"},
    "revoke": {"oidc_issuer": "https://token.actions.githubusercontent.com", "identity": "https://github.com/rockmed888-ship-it/ldtt/.github/workflows/ldtt-revoke.yml@refs/heads/main"}
  },
  "artifact_signers": {
    "<connector_id>": {"oidc_issuer": "https://token.actions.githubusercontent.com", "identity": "<release workflow identity>"}
  }
}
```
`trust_root_version` is monotonic. Connectors still pin the Issuer and Revoke identities in code; this file never overrides those pins.

### F.4 PLAN REF — reference checkers [N31]
Before any **v0.2** stamp of a reference connector, its revocation checker must conform to this draft: Revoke-or-Issuer list verify, `base` + append-only + base floor, Q-C2 equal-version reject, §A.3.6 time check, and C4 fail-closed (including session TX+RX halt as in the mavsdk-observer F1/F5a pattern). **PLAN REF only** — no checker code in this draft. Open Builder owns the conformance work later.


---

## E. Open questions for Lead

**Resolved:**
- Q-A1 → M1 (split identities).
- Q-B2 → not stampable.
- Q-C1 → N7 rule + M6.
- R1 → base pointer (Lead-locked).
- R3 → rollback = immediate fail closed (Lead pick a).
- Q-C2 → same `list_version` with different bytes = rollback = immediate fail closed (Lead-locked, §C.4).
- Q-A5 → accepted (300 s / 3600 s, given R2).
- **Q-A2 Lead lean (not frozen):** GitHub Actions + Sigstore keyless only for v0.2; no alternate private CA / non-GitHub OIDC.

**Still open:**
1. **Q-B1 (awaiting user):** can BlueOS install an extension pinned by image digest? This decides whether BlueOS unblocks.
2. **Q-A3:** offline verification. Should connectors ship a cached Sigstore trusted root, and how often must it be refreshed?
3. **Q-A4 (Lead lean, not frozen):** prefer a ruleset bypass if the tier allows it. Otherwise drop "require pull request" on `main`, with force-push/delete blocked, path-scoped publish, and §A.3.10 monitoring. Environment `ldtt-issuer` is Lead-created before Issuer runs (see §A.2 box-workflow note). Still to confirm on the real repo.
4. **Q-D1 (P12):** may Observe change stream rates while another ground station is connected?
5. **Q-Q11:** confirm `connector.package_version` (now listed in §F.1) rather than relaxing the `version` pattern.

*FROZEN r5.1 · publish-ready (Spec + FREEZE only). LDTT is a connector stamp only: not aircraft certification, not a fleet dashboard, no FAA or airworthiness claims.*
