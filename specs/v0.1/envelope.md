# crtx v0.1 — Envelope, Turn, ContentPart

**Status:** Draft  
**Schema URL:** `https://spec.hop.top/crtx/v0.1/envelope.schema.json`  
**License:** CC-BY-4.0

This document specifies the on-the-wire and on-disk shape of an AI
agent conversation. It is the contract that
[`stem`](https://github.com/hop-top/poly-stem) produces,
[`vein`](https://github.com/hop-top/vein) indexes, and
[`nerv`](https://github.com/hop-top/nerv) carries.

The spec is **transport-agnostic**: a crtx Envelope can be a JSON
document on disk, a row in SQLite, a JSONL line, a Connect/gRPC
message, or a Kafka record. Wire framing is the concern of the
consuming tool.

---

## 1. Terminology

| Term | Meaning |
|------|---------|
| **Envelope** | One conversation. Contains metadata + an ordered list of Turns. |
| **Turn** | One contribution from one role. May contain multiple ContentParts. |
| **ContentPart** | One unit of payload inside a Turn: text, tool call, tool result, image, etc. |
| **Role** | Who produced the Turn: `user`, `assistant`, `tool`, `system`, `developer`. |
| **Source** | The runtime that produced the Envelope (e.g. `stem v0.1.0`, `claude-code v1.2`). |
| **Fork** | A child Envelope that inherits its parent's Turns up to a point. See [§7.1](#71-what-if-forks). |
| **Dispatch nest** | A child Envelope spawned by an open `tool_call` in a parent Envelope; runs as a fresh session with curated context. See [§7.2](#72-dispatch-nests). |
| **Injected turn** | A reference, from one Envelope, to a slice of Turns in another Envelope, included as part of the referencing Envelope's context. See [§7.3](#73-injected-turns). |

"MUST", "SHOULD", "MAY" follow [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 2. Envelope

The top-level container.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `crtx_version` | string | yes | Spec version. v0.1 envelopes MUST use `"0.1"`. |
| `id` | string | yes | Globally unique. ULID or UUIDv7 RECOMMENDED. |
| `created_at` | string (RFC 3339) | yes | When the conversation started. |
| `updated_at` | string (RFC 3339) | yes | Last mutation. Producers MUST update this on every append. |
| `source` | [Source](#5-source) | yes | Producing runtime. |
| `turns` | array of [Turn](#3-turn) | yes | Ordered. May be empty. |
| `parent_id` | string | no | If set, this Envelope is a fork of `parent_id`. See [§7.1](#71-what-if-forks). |
| `fork_point` | integer | no | Index into the parent's `turns` array at which the fork branched. REQUIRED if `parent_id` is set. MUST NOT be set if `dispatched_from` is set. |
| `dispatched_from` | object | no | When set, this Envelope was spawned by an open `tool_call` in another Envelope as a dispatch nest. Schema: `{ envelope_id: string, call_id: string }`. Both members REQUIRED. Mutually exclusive with `parent_id` / `fork_point`. See [§7.2](#72-dispatch-nests). |
| `injected_turns` | array | no | Foreign Turn slices referenced as part of this Envelope's context. Append-only. See [§7.3](#73-injected-turns). |
| `metadata` | object | no | Free-form. Keys SHOULD be reverse-DNS (`io.jadb.tag`) to avoid collisions. |

**Append-only semantics.** Producers SHOULD treat `turns` as
append-only after the first persist. Editing prior Turns breaks
reproducibility for downstream consumers (vein, replay tools).
Mutations that *must* happen (redaction, retraction) MUST be
represented as a new Turn with role `system` and an explicit
`metadata.retracts: <turn_id>` pointer.

**Identity.** `id` is stable for the lifetime of the conversation
across forks, restarts, and re-indexing. Implementations MUST NOT
re-mint an `id` for the same logical conversation.

---

## 3. Turn

One contribution to the conversation.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Unique within the Envelope. ULID RECOMMENDED. |
| `role` | [Role](#4-role) | yes | Producer of this Turn. |
| `created_at` | string (RFC 3339) | yes | When this Turn was produced. |
| `content` | array of [ContentPart](#6-contentpart) | yes | Ordered. MUST contain ≥1 part. |
| `agent_id` | string | no | Stable identifier of the producing agent when multiple assistants contribute to one Envelope. See [§3.1](#31-multi-agent-provenance). |
| `in_reply_to_call_id` | string | no | If set, MUST reference a `tool_call.call_id` earlier in the Envelope whose matching `tool_result` has not yet appeared at or before this Turn. Marks this Turn as a mid-flight message into the lifetime of that call. See [§3.2](#32-mid-flight-messaging). |
| `metadata` | object | no | Free-form, same conventions as Envelope. |

**Ordering.** Turns in `Envelope.turns` are ordered by their position
in the array, NOT by `created_at`. Producers MAY persist Turns
out-of-order in time (e.g. tool execution overlapping with streaming
assistant output) but the array order is canonical.

**Atomicity.** A Turn is the atomic unit of append. Consumers MUST
NOT observe a Turn before all its `content` parts are finalized. A
Turn has exactly one producer; per-ContentPart attribution is not
defined.

### 3.1 Multi-agent provenance

`agent_id` attributes a Turn to a specific producing agent. It is
OPTIONAL and applies to any Turn whose `role` is `assistant`, `tool`,
or `developer`. Absence means the producer is the Envelope's
[`source`](#5-source).

- The identifier is opaque to the spec. Implementations MAY use
  short labels (`"C"`, `"orchestrator"`), ULIDs, or vendor-specific
  ids. Stability across Turns within one Envelope is REQUIRED;
  stability across Envelopes is RECOMMENDED.
- Producers SHOULD either set `agent_id` on every applicable Turn in
  an Envelope or omit it from all of them. Mixed envelopes force
  consumers to guess attribution for the unannotated Turns.
- `user` and `system` Turns SHOULD NOT carry `agent_id`. The user is
  the human; the system Turn is host-runtime metadata.

When sub-agent dispatch is expressed in-band as nested tool calls,
pair `agent_id` with [`tool_call.parent_call_id`](#62-tool_call) to
make the dispatch tree machine-recoverable.

### 3.2 Mid-flight messaging

While a `tool_call` is open (no matching `tool_result` yet), other
participants MAY append Turns into the Envelope that target the
dispatched work. A Turn with `in_reply_to_call_id` set to an open
call's `call_id` is such a mid-flight message: an interjection,
clarification, scope change, cancellation request, or progress
note directed at the agent executing that call (or, equivalently,
at the agent that issued it, if the producer is the executor).

This spec is **deliberately permissive** about *who* may interject:

- The producer's `agent_id` MAY equal the issuer of the referenced
  call (the dispatcher messaging the executor), the executor itself
  (interim status into its own outer call), or any third party that
  the runtime considers authorized.
- The producer's `role` MAY be any value; conventional choices are
  `user` (orchestrator-to-executor or human-to-executor), `developer`
  (high-priority guidance), or `system` (host-runtime guardrail).
  `tool` is reserved for `tool_result` Turns and SHOULD NOT carry
  `in_reply_to_call_id`.

Runtimes that need stricter rules — for example, "only the call's
issuer may interject," or "no interjection once the executor has
started emitting `tool_call` parts" — SHOULD enforce them outside
the envelope: in dispatcher policy, transport-layer auth, or a
schema overlay. The on-the-wire shape stays portable.

This spec is silent on how an executor's eventual `tool_result`
relates to interjections that targeted its open call. Whether the
result acknowledges, ignores, or supersedes them is a runtime
concern (see [`stem`](https://github.com/hop-top/poly-stem)).

Lifetime invariant. The referenced `tool_call.call_id` MUST be an
unresolved call at the point this Turn is appended. Once the
matching `tool_result` lands, the call is closed and no further
Turns MAY reference it via `in_reply_to_call_id`.

Pairing with `agent_id`. When both fields are set, a consumer can
reconstruct the routing intent without parsing content:
*"`{Turn.agent_id}` sent this to the agent running `{in_reply_to_call_id}`."*

---

## 4. Role

Enum.

| Value | Meaning |
|-------|---------|
| `user` | A human-originated message. |
| `assistant` | LLM-generated output. |
| `tool` | The result of a tool invocation. Pairs with a preceding `assistant` Turn containing a `tool_call`. |
| `system` | Instructions from the host runtime. SHOULD appear at most once, at index 0. |
| `developer` | Higher-priority instructions than `system`, lower than `user`. Optional; mirrors OpenAI's developer-role convention. |

Implementations encountering an unknown role MUST reject the
Envelope rather than coerce.

---

## 5. Source

Identifies the runtime that produced the Envelope. Vein uses this to
route through the right adapter; replay tools use it to pick a
compatible interpreter.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `kind` | string | yes | Tool family. Recommended values: `stem`, `claude-code`, `codex`, `gemini-cli`, `opencode`, `custom`. |
| `version` | string | yes | Semver string of the producing tool. |
| `instance` | string | no | Free-form identifier for this producer instance (hostname, PID, session id). |

---

## 6. ContentPart

A single payload unit inside a Turn. ContentParts are **discriminated
unions** on the `type` field.

Common fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | string | yes | Discriminator. v0.1 enum: `text`, `tool_call`, `tool_result`, `image`, `thinking`. |
| `metadata` | object | no | Free-form, same conventions as elsewhere. |

### 6.1 `text`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `text` | string | yes | Plain text. Markdown is allowed but not normalized. |

### 6.2 `tool_call`

Issued by the assistant.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `call_id` | string | yes | Unique within the Envelope. Matched by the responding `tool_result`. |
| `name` | string | yes | Tool name. |
| `input` | object \| string | yes | Arguments. Object form is canonical; string form is permitted for legacy / streaming chunks. |
| `parent_call_id` | string | no | If set, MUST reference a `tool_call.call_id` that appears earlier in the Envelope and has not yet been matched by a `tool_result` at or before this Turn. Indicates this call was issued while executing the parent call (nested dispatch, sub-tool, etc.). Chains of any depth are permitted. |

### 6.3 `tool_result`

Issued by the `tool` role in response to an earlier `tool_call`.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `call_id` | string | yes | MUST match a preceding `tool_call.call_id` in the same Envelope. |
| `output` | any | yes | Tool output. JSON-serializable. |
| `is_error` | boolean | no | Default `false`. When `true`, `output` SHOULD be a human-readable error description. |
| `child_envelope_id` | string | no | When the call was executed out-of-band in a [dispatch nest](#72-dispatch-nests), points at the child Envelope's `id`. Consumers MAY follow it to the full child transcript. |

### 6.4 `image`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `mime` | string | yes | E.g. `image/png`. |
| `data` | string | one of | Base64-encoded image bytes. |
| `url` | string | one of | URL to fetch the image. Exactly one of `data` / `url` MUST be set. |
| `alt` | string | no | Alt text. |

### 6.5 `thinking`

Reserved for chain-of-thought / reasoning traces emitted by models
that expose them (e.g. Claude extended thinking).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `text` | string | yes | Reasoning trace. |
| `signature` | string | no | Provider-supplied signature for replay/verification. |

Consumers MAY drop `thinking` parts during display without violating
spec compliance.

### 6.6 Extension parts

Implementations MAY emit ContentParts with `type` values prefixed
`x-` (reverse-DNS recommended: `x-io.jadb.custom`). Consumers
encountering an unknown `type` MUST preserve the part verbatim when
forwarding the Envelope, and MAY ignore it when rendering.

---

## 7. Child Envelopes and external context

A child Envelope is one whose existence references another Envelope.
v0.1 defines three relationships, each with distinct semantics:

| Relationship | Field(s) | Inherits history? | Use case |
|--------------|----------|-------------------|----------|
| What-if fork | `parent_id` + `fork_point` | Yes (up to `fork_point`) | Explore an alternative path |
| Dispatch nest | `dispatched_from` | No | Spawn a sub-agent with curated context |
| Injection | `injected_turns` | Cherry-picked slices | Pull foreign Turn ranges into context |

A child Envelope MUST NOT set both `parent_id` and `dispatched_from`.
The two relationships are mutually exclusive. `injected_turns` is
orthogonal and MAY appear with either, or on a standalone Envelope.

### 7.1 What-if forks

A fork creates a new Envelope that shares history with its parent up
to a given Turn index. Forks are RECOMMENDED over editing prior
Turns when an agent or user wants to explore an alternative path.

```text
parent envelope:  [t0 t1 t2 t3 t4]
                          ↑
                     fork_point = 2

child envelope:   parent_id = <parent.id>
                  fork_point = 2
                  turns     = [t3' t4' …]   # child's own continuations
```

The child's `turns` array contains ONLY the Turns produced after the
fork. Consumers reconstruct the full conversation by concatenating
the parent's `turns[0:fork_point+1]` with the child's `turns`.

Forks of forks are permitted. `parent_id` chains MAY be of any depth.

### 7.2 Dispatch nests

A dispatch nest is a child Envelope spawned by an open `tool_call` in
a parent Envelope, used when the executor of that call runs as a
fresh session rather than in-band as additional Turns of the parent.

```text
parent envelope:                     dispatch-nest child envelope:
  turns: [...]                         dispatched_from:
    ├─ tool_call(call_id=X) ◄──────┐     envelope_id = <parent.id>
    └─ (later) tool_result(X)        │   call_id     = X
         child_envelope_id = <child.id>
                                     └ turns: [...]   # fresh session
```

Unlike a fork, a dispatch nest does NOT inherit the parent's history.
The child's `turns` are independent; the runtime curates whatever
context the child should see, typically as a synthesized first Turn
(role `user` or `system`) and/or as [injected turns](#73-injected-turns).

The parent Envelope MUST still receive a matching `tool_result` Turn
to close the open `tool_call`. That `tool_result` SHOULD set
`child_envelope_id` to the dispatch-nest child's `id`, so the
parent's transcript remains complete on its own (lifetime invariant
in [§6.2](#62-tool_call)) and consumers can walk to the child.

Dispatch nests MAY be nested: a dispatch-nest child can itself open
a `tool_call` that spawns a grandchild dispatch nest. `dispatched_from`
chains MAY be of any depth.

When the parent's runtime expresses dispatch in-band (executor's
Turns appended to the parent Envelope, glued by
[`tool_call.parent_call_id`](#62-tool_call)) no dispatch nest is
required. The choice between in-band and out-of-band is a runtime
concern.

### 7.3 Injected turns

`Envelope.injected_turns` is an ordered, append-only list of
references to Turn slices in other Envelopes. Each entry has the
shape:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `envelope_id` | string | yes | The source Envelope's `id`. |
| `start_turn_id` | string | yes | First Turn in the slice (inclusive). |
| `end_turn_id` | string | yes | Last Turn in the slice (inclusive). MUST be at or after `start_turn_id` in the source Envelope's `turns` array. For a single-Turn pick, set equal to `start_turn_id`. |
| `injected_after_turn_id` | string | no | When set, this entry is inserted into the local timeline immediately after the named Turn (which MUST already exist in this Envelope's `turns` at the time the entry is appended). When absent, the entry is conceptually prepended before `turns[0]` (creation-time injection). |

**Append-only.** Once persisted, an entry MUST NOT be modified or
removed. New entries MAY be appended at any time. Forward references
(`injected_after_turn_id` pointing at a Turn not yet present) are
forbidden: reading state at any point in time MUST yield an
unambiguous reconstruction.

**Reconstruction algorithm.** To produce the full conversation as a
consumer should view it:

1. Start with this Envelope's `turns` as the base timeline.
2. For each entry in `injected_turns` with no `injected_after_turn_id`,
   prepend the referenced slice to the base timeline in array order.
3. For each entry with `injected_after_turn_id` set, insert the
   referenced slice immediately after the named Turn. If multiple
   entries target the same `injected_after_turn_id`, order them by
   their position in `injected_turns` (earlier entries come first).
4. Slices themselves are resolved against the source Envelope at
   read time: retractions, redactions, and other system Turns in
   the source remain observable.

**Audit Turn (recommended).** Producers SHOULD also append a Turn to
this Envelope's `turns` recording the injection event (e.g. a
`system`- or `user`-role Turn carrying the import command text).
The structural `injected_turns` entry is the machine-readable shape;
the audit Turn preserves the timeline of *when* the injection was
requested. They are complementary, not duplicates.

**Cross-source resolution.** The spec does not define how a consumer
locates a referenced `envelope_id` — that is a registry or
transport-layer concern. Consumers MAY refuse to render Turns from
envelopes they cannot resolve.

---

## 8. Versioning

- The spec version is the directory name under `specs/` and the value
  of `Envelope.crtx_version`.
- Within a major version, fields MAY be added but MUST be optional.
- Removed or renamed fields, or changed semantics, require a new major
  version directory.
- Consumers MUST reject Envelopes whose `crtx_version` major does not
  match a supported version.

---

## 9. Validation

Every Envelope MUST validate against the JSON Schema at
[`envelope.schema.json`](envelope.schema.json) for the declared
`crtx_version`. The schema is the authoritative machine-checkable
expression of this document; in case of conflict between schema and
prose, **the schema wins** for a given tagged version.

---

## 10. Open questions for v0.1 → v0.2

- Streaming: how to represent partial Turns that have not yet
  finalized. Current thinking: a `status: "open" | "finalized"` field
  on Turn, with consumers ignoring open Turns by default.
- Citations / source attributions inside `text` parts.
- Audio / video ContentPart types.
- Cost / token-usage accounting — Envelope-level vs. Turn-level.

These are deliberately out of scope for v0.1 to keep the surface
small while real implementations land.

---

**See also:** [`events.md`](events.md) — canonical bus topic names
and payload shapes for live emission of the Turns and ContentParts
defined above.
