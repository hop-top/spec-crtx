# crtx — agent steering

This repository owns the **language-agnostic** specification for AI
agent conversations. It ships no executable code (except validators
and CI helpers under `.github/scripts/`).

## Editing rules

- **Spec doc and schema move together.** Any change to
  `specs/<v>/envelope.md` MUST land with matching changes to
  `envelope.schema.json` in the same commit. CI rejects drift.
- **Examples are tests.** Files under `specs/<v>/examples/` MUST
  validate against `envelope.schema.json` for that version.
- **Versions are immutable once tagged.** After `crtx/v0.1.0` ships,
  edits to `specs/v0.1/` are limited to clarifications that do not
  change validation outcomes (typo, prose). Substantive changes
  open a new minor (`v0.2`).
- **Breaking changes bump the major.** Field rename, type change,
  enum-value removal → new major version directory (`specs/v1/`).

## What belongs here

- Envelope, Turn, ContentPart, Role, Source.
- Tool-call and tool-result shape (including `tool_result.child_envelope_id`).
- Forks (`parent_id` + `fork_point`), dispatch nests (`dispatched_from`),
  and injected turns (`injected_turns`).
- Multi-agent provenance (`Turn.agent_id`, `Turn.in_reply_to_call_id`,
  `tool_call.parent_call_id`).
- Versioning + schema-URL convention.

## What does NOT belong here

- Runtime behaviour (depth limits, supervisor) → [`stem`](https://github.com/hop-top/poly-stem).
- Search/index shape → [`vein`](https://github.com/hop-top/vein).
- Transport (wire protocol, auth) → consuming tools.
- Provider-specific request shapes (OpenAI / Anthropic / Gemini).

## Commits

Conventional Commits with bare types — `feat:`, `fix:`, `docs:`,
`chore:`, `build:`, `refactor:`, `test:`, `ci:`. No scope on routine
work. Scope reserved for release tooling (`chore(release): ...`,
managed by release-please).
