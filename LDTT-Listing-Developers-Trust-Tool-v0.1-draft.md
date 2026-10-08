# Listing Developers Trust Tool (LDTT) — MCP line, draft v0.1

**Status:** DRAFT. Not frozen. Not a real stamp. Not signed by `ldtt-issue.yml`.
**Date:** 2026-10-08
**Owner:** Dustin Dent · **Repo:** `rockmed888-ship-it/ldtt`
**$0.** No card numbers. No model keys in this file.

LDTT keeps two lines on one issuer:

| Line | Name | Spec | What it stamps |
|---|---|---|---|
| Drone | Linked Drone Tool Trust | Frozen Spec v0.2 / connector spec v0.1.4 | Drone software connectors only |
| MCP | Listing Developers Trust Tool | This draft | MCP and other tool connectors |

The drone spec is not rewritten. A drone stamp is still not aircraft, pilot, or FAA approval. An MCP stamp is still not a promise that an AI is safe, and it is not an order that Google, xAI, Anthropic, or OpenAI must comply.

## 1. What is valuable

A host that checks the stamp before it loads a custom connector can refuse three abuses:

- The connector asks for or stores a model API key, or hands that key to the customer.
- The connector calls a tool, or opens a network path, that the stamp did not declare.
- The connector sends, posts, pays, publishes, or deletes when the stamp says a person must do that.

That is the protection. A stamp nobody checks does not stop a malicious server. A company that has not agreed to check LDTT is not "in violation." The path is to stamp connectors we own, then ask hosts to refuse unstamped custom connectors. Cooperation is adoption. It is not something this repo can force.

## 2. Rule

A listing is **real** only after the same rule as Spec v0.2 §A.1: keyless signature by `ldtt-issue.yml` on `main`, verifying as the Issuer identity. Until then every file under `listings/` is an owner draft. `real_stamp` must be `false`. Do not copy these files into `stamps/` and do not dispatch `ldtt-issue` mode `stamp` for them.

Placeholder-key signatures do not count.

## 3. Controls (every MCP listing)

| ID | Control | Fail closed when |
|---|---|---|
| M1 | Declared tools | A real stamp's tool list was not taken from a live `tools/list`. A draft may say `tools_evidence: owner-declaration`. |
| M2 | No model key | `model_key_leaves_host` or `customer_receives_api_key` is true, or the file contains a key, bearer token, or private URL token. |
| M3 | Egress | `undeclared_egress` is anything but `deny`. |
| M4 | Human gates | A connector that can act omits `send`, `post`, or `pay` from `human_gates`. |
| M5 | Revocation | Uses the LDTT list once the Issuer base exists. This draft does not point `list_url` at a keyless list while the connector still verifies only the placeholder key. |
| M6 | Honest host claim | `host_enforcement` names a company that has not shipped an LDTT check. Allowed value today: `none`. |

C9-style product limits stay in `known_limitations`. Do not delete a limit to make the listing look finished.

## 4. First proofs (owner drafts)

These are connectors and one site Dustin Dent owns and already runs. They prove the listing shape. They are not active stamps.

| Listing | What it is | Evidence used |
|---|---|---|
| `org.ldtt.brain-connector` | Brain Connector MCP. Customer never receives the model key. Send, post, and pay stay with the person. | Shop and public site behavior recorded 2026-10-04. Private shop repo stays private. |
| `org.ldtt.dent-coins` | Host proof for https://dtfdentcoin.com. Physical-coin marketplace. Uses the Brain Connector. Not itself an MCP server. Not a cryptocurrency. | Live site and the Dent tools on the shared brain. |
| `org.ldtt.brand-agents-dd` | Brand Agents phone-hands MCP (`dd`). Tools `dd_status`, `dd_run`, `dd_open`, `dd_observe`, `dd_continue`, `dd_stop`. Send, post, pay, and publish wait for the person. Passwords and 2FA stop the agent. | Local DD connector record. Pairing bearer stays out of this repo. |
| `org.ldtt.brand-agents` | Host proof for https://brandbyagents.com. Cody is the public face. Uses the DD hands connector. Not itself an MCP server. | Public site and the DD tool record. |

Queued, no listing file yet, because their `tools/list` has not been read: Dale Ray, RailWorks, SBA Path, and Reel Desk. A name in the Grok MCP config is not a tool allowlist. Dale Ray is a separate installer desk, not the DD connector.

Northwind is a Brain Connector website plug (`bc_1a103677254`) and stays under the Brain Connector listing until its own `tools/list` is recorded. No separate stamp.

## 5. Path to a real MCP stamp

1. **L0 (this draft).** Name the line. Publish owner listings with `real_stamp: false`. Checker rejects a listing that claims a real stamp or a host enforcement that does not exist.
2. **L1.** Issuer scripts and unsigned `trust/trust-root.json` on `main`. Issue the keyless revocation base and trust root. Do not sign these listings in that run.
3. **L2.** Read `tools/list` from each owned connector. Replace `owner-declaration` with that list. Add the hash-locked digest when there is a release file to bind.
4. **L3.** MCP checker in the connector: declared tools only, M2–M4, revocation. Same fail-closed bar as the drone observer. No v0.2 stamp field on a connector that cannot enforce it.
5. **L4.** One keyless Issuer signature for `org.ldtt.brain-connector` after L2 and L3 pass. That is the first real Listing Developers Trust Tool stamp. The drone stamp `0.1.0` stays a draft until its own P5 provenance is green and its C3 text is true.
6. **L5.** On this PC, Grok refuses a custom MCP server that has no matching listing. Write the check into the host we control. Document the invite for other hosts. Do not say they already cooperate.

## 6. Non-goals

- Forcing Google, xAI, Anthropic, OpenAI, or any other host to adopt LDTT.
- Certifying an AI model, a chat, or a person.
- Hiding the private Brain Connector shop or putting its keys in this repo.
- Relabeling the placeholder drone stamp as active.
