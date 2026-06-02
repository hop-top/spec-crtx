# crtx (pronounced "cortex")

> [!WARNING]
> **Alpha — spec is unstable.** The on-the-wire shape will change.
> Pin to a specific spec version (`v0.1`, `v0.2`, …) — do not track
> `main`. See [`specs/v0.1/CHANGELOG.md`](specs/v0.1/CHANGELOG.md)
> for the v0.1 change history.

Language-agnostic specification for AI agent conversations: sessions,
turns, content parts, tool calls, and the envelope that carries them.

`crtx` defines the **wire and storage shape** that the rest of the
runtime stack agrees on:

| Tool | Role | What it does with crtx |
|------|------|------------------------|
| [`vein`](https://github.com/hop-top/vein) | Cross-CLI index | Maps Claude Code / Codex / Gemini / OpenCode transcripts → crtx envelope |
| [`nerv`](https://github.com/hop-top/nerv) | Signal wire | Routes crtx turns between agents |
| [`stem`](https://github.com/hop-top/poly-stem) | Agent runtime | Produces crtx envelopes from live agent loops |

crtx itself ships **no code**. It is a spec repo: a Markdown
description, a JSON Schema, and a set of conformance examples.
Implementations live in their respective tool repos.

## Spec versions

| Version | Status | Source of truth |
|---------|--------|-----------------|
| [`v0.1`](specs/v0.1/) | Draft | [`specs/v0.1/envelope.md`](specs/v0.1/envelope.md) (envelope shape) + [`specs/v0.1/events.md`](specs/v0.1/events.md) (bus event taxonomy) |

Versions are independent: an implementation may speak v0.1 and v0.2
side-by-side, dispatched by the `crtx_version` field in the envelope.

## How to read this repo

1. Start with the spec doc: [`specs/v0.1/envelope.md`](specs/v0.1/envelope.md).
2. Validate against the schema: [`specs/v0.1/envelope.schema.json`](specs/v0.1/envelope.schema.json).
3. See real envelopes: [`specs/v0.1/examples/`](specs/v0.1/examples/).
4. Conformance suite: [`specs/v0.1/conformance/`](specs/v0.1/conformance/) _(planned)_.

## What's NOT in scope

- **Runtime semantics** — scheduling, retry policy, depth limits,
  dispatcher behavior — see [`stem`](https://github.com/hop-top/poly-stem).
  crtx records _that_ a dispatch happened (via `agent_id` and
  `tool_call.parent_call_id`); it does not define _how_.
- **Index / search shape** — see [`vein`](https://github.com/hop-top/vein).
- **Provider adapters** (OpenAI / Anthropic / Gemini request format) —
  out of scope; crtx is provider-agnostic.
- **Authentication / authorization** — transport-layer concern.

## License

CC-BY-4.0 for the spec text and schema; MIT for any example code.
See [`LICENSE`](LICENSE).
