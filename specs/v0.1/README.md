# crtx v0.1

**Status:** Draft  
**Last updated:** 2026-05-28

This is the first published version of the crtx envelope spec.

## Files

| File | What |
|------|------|
| [`envelope.md`](envelope.md) | Envelope prose specification. Read this first. |
| [`envelope.schema.json`](envelope.schema.json) | Envelope JSON Schema 2020-12. Authoritative validator. |
| [`events.md`](events.md) | Event taxonomy prose specification (bus topic names + payload shapes). |
| [`events.schema.json`](events.schema.json) | Event payload JSON Schema 2020-12. Authoritative validator. |
| [`examples/minimal.json`](examples/minimal.json) | Smallest valid Envelope (one user + one assistant turn). |
| [`examples/tool-call.json`](examples/tool-call.json) | Full assistant→tool→tool_result→assistant flow. |
| [`examples/fork.json`](examples/fork.json) | Child Envelope that forks from a parent. |
| [`examples/dispatch.json`](examples/dispatch.json) | In-band nested sub-agent dispatch using `agent_id` + `parent_call_id`. |
| [`examples/dispatch-nested.json`](examples/dispatch-nested.json) | Out-of-band dispatch nest (child Envelope with `dispatched_from`). |
| [`examples/injection.json`](examples/injection.json) | Mid-session foreign-Turn injection via `/import`. |
| [`examples/events/`](examples/events/) | Concrete payload examples for every canonical event topic. |

## Conformance (planned)

A conformance runner will live under `conformance/` once the spec
ships its first tagged release. It will:

1. Validate every example against `envelope.schema.json`.
2. Run cross-implementation round-trips (stem-go, stem-ts, vein adapters).
3. Verify reconstruction semantics: parent ⊕ fork = full conversation.
