# LDTT

Connector trust stamp. Two lines, one issuer.

| Line | Name | Status |
|---|---|---|
| Drone | Linked Drone Tool Trust | Frozen spec v0.2. Reference stamp `0.1.0` is still a **draft** placeholder, not a real stamp. |
| MCP | [Listing Developers Trust Tool](./LDTT-Listing-Developers-Trust-Tool-v0.1-draft.md) | Draft v0.1. Owner listings only. Not signed. |

- Drone spec (current connector spec): [`LDTT-Stamp-Spec-v0.1.4.md`](./LDTT-Stamp-Spec-v0.1.4.md)
- Frozen trust-root spec: [`LDTT-Stamp-Spec-v0.2.md`](./LDTT-Stamp-Spec-v0.2.md)
- Schema: [`schema/ldtt.schema.json`](./schema/ldtt.schema.json)
- Drone reference connector: [`ref-connectors/ldtt-ref-mav-observer/`](./ref-connectors/ldtt-ref-mav-observer/)
- MCP owner listings: [`listings/`](./listings/)

LDTT stamps connectors only. It does **not** certify aircraft, operators, airworthiness, or flight safety, and makes no FAA or other regulatory claim. An MCP listing does **not** make Google or any other host comply. A host protects the user only when that host checks the stamp before loading a custom connector.

## License

Apache-2.0 for project docs/schema unless a subdirectory says otherwise.
