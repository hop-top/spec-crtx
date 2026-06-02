# crtx v0.1 — Event Taxonomy

**Status:** Draft
**Schema URL:** `https://spec.hop.top/crtx/v0.1/events.schema.json`
**License:** CC-BY-4.0

This document specifies the canonical **bus topic names** and
**payload shapes** for live AI agent events. It complements
[`envelope.md`](envelope.md): the envelope spec defines the
authoritative on-disk / on-wire shape of a conversation; this spec
defines how the same conversation is published to a bus while it
unfolds.

The taxonomy is **transport-agnostic**: any bus with topic + payload
semantics (Kafka, NATS, in-process channel, HTTP webhook, etc.) can
carry crtx events. Wire framing is the concern of the consuming
transport.

The central design invariant: **every event payload IS a valid crtx
ContentPart or Envelope metadata fragment**. A recorder subscribed
to canonical topics can append straight to a crtx Envelope without
translation.

---

## 1. Terminology

| Term | Meaning |
|------|---------|
| **Event** | A single notification published on a bus topic when something happens inside a conversation. |
| **Topic** | A bus subject name. See §2 for the naming convention. |
| **Payload** | The data carried by an event. Always shaped as a crtx ContentPart or Envelope metadata fragment. |
| **Producer** | The runtime that emits events (typically the same process producing the [Envelope](envelope.md#2-envelope)). |
| **Subscriber** | A consumer that observes events (indexer, dashboard, recorder, replay tool). |

The [Envelope](envelope.md#2-envelope), [Turn](envelope.md#3-turn),
and [ContentPart](envelope.md#6-contentpart) types are defined in
[`envelope.md`](envelope.md) and referenced here without repetition.

"MUST", "SHOULD", "MAY" follow
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 2. Topic naming convention

Canonical topics use four dot-separated parts:

```
crtx.<category>.<object>.<action>
```

- `<category>` groups the event by lifecycle layer. v0.1 defines two:
  - `turn` — events about a single Turn appended to an Envelope.
  - `session` — events about an Envelope as a whole.
- `<object>` names the specific entity within the category:
  - `turn` category: a Role value (`user`, `assistant`, `tool`,
    `system`, `developer`) or a ContentPart type that is
    Turn-bound (`thinking`).
  - `session` category: `envelope`.
- `<action>` is a past-tense verb describing what happened
  (`received`, `emitted`, `called`, `completed`, `injected`,
  `created`, `forked`, `nested`, `returned`).
- Lowercase only. Dot-separated. No underscores. No camelCase.

The `crtx.*` namespace is reserved for this spec. Implementations
MUST NOT invent new topics under `crtx.*`. Extension topics MUST
use a vendor prefix (`x.<vendor>.*`) — see §5.

---

## 3. Canonical topics — v0.1

This section is normative. Every payload field name uses the same
snake_case convention as the wire-format envelope. Where a payload
field has a counterpart in [`envelope.schema.json`](envelope.schema.json),
the semantics are identical.

| Topic | When emitted | Payload fields |
|-------|-------------|----------------|
| `crtx.turn.user.received` | Producer accepts a user message. | `envelope_id`, `turn_id`, `content`, `in_reply_to_call_id?` |
| `crtx.turn.assistant.emitted` | Provider finalizes an assistant response (including streaming completion). | `envelope_id`, `turn_id`, `content`, `agent_id?`, `in_reply_to_call_id?` |
| `crtx.turn.tool.called` | Assistant emits a `tool_call` ContentPart. | `envelope_id`, `turn_id`, `call_id`, `name`, `input`, `parent_call_id?`, `agent_id?` |
| `crtx.turn.tool.completed` | Tool handler returns a result. | `envelope_id`, `turn_id`, `call_id`, `output`, `is_error?`, `child_envelope_id?`, `agent_id?` |
| `crtx.turn.thinking.emitted` | Reasoning trace produced by a model that exposes it. | `envelope_id`, `turn_id`, `text`, `signature?`, `agent_id?`, `in_reply_to_call_id?` |
| `crtx.turn.system.injected` | Host-initiated `system` Turn added. | `envelope_id`, `turn_id`, `content`, `in_reply_to_call_id?` |
| `crtx.session.envelope.created` | New Envelope materialized. | `envelope_id`, `created_at`, `source`, `injected_turns?` |
| `crtx.session.envelope.forked` | What-if fork: child Envelope inherits parent history. | `parent_id`, `child_id`, `fork_point`, `created_at` |
| `crtx.session.envelope.nested` | Dispatch nest: child Envelope spawned by an open tool_call as a fresh session. | `parent_id`, `child_id`, `call_id`, `created_at` |
| `crtx.session.envelope.returned` | A dispatch-nest child's result has been folded back into the parent as a `tool_result`. | `parent_id`, `child_id`, `call_id`, `created_at`, `is_error?` |

`agent_id` carries the producing agent's identifier when the Envelope
hosts multiple assistants (see [envelope.md §3.1](envelope.md#31-multi-agent-provenance)).
Producers SHOULD emit it on every applicable topic when they emit it
on any. `parent_call_id` mirrors
[`tool_call.parent_call_id`](envelope.md#62-tool_call) for nested
calls. `in_reply_to_call_id` mirrors
[`Turn.in_reply_to_call_id`](envelope.md#3-turn) for mid-flight
messaging (see [envelope.md §3.2](envelope.md#32-mid-flight-messaging)).
The `crtx.turn.tool.called` and `crtx.turn.tool.completed` topics
deliberately do not carry `in_reply_to_call_id`: tool Turns are
call-mechanic events, not interjections.

### 3.1 `crtx.turn.user.received`

Emitted when the producer accepts a user-originated message and
appends it as a Turn with `role: "user"`.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `envelope_id` | string | yes | The Envelope this Turn belongs to. |
| `turn_id` | string | yes | The Turn id assigned by the producer. |
| `content` | array of [ContentPart](envelope.md#6-contentpart) | yes | The Turn's content. Typically a single `text` part; MAY include `image` parts. |
| `in_reply_to_call_id` | string | no | When the user message targets an in-flight dispatched call. Matches the Turn's `in_reply_to_call_id`. See [envelope.md §3.2](envelope.md#32-mid-flight-messaging). |

### 3.2 `crtx.turn.assistant.emitted`

Emitted when a provider finalizes an assistant response. For
streaming providers, this is published once at stream end (the
"finalized" moment), not per chunk. Streaming-chunk events are
deferred to a future spec version (see §9).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `envelope_id` | string | yes | |
| `turn_id` | string | yes | |
| `content` | array of [ContentPart](envelope.md#6-contentpart) | yes | MAY contain a mix of `text` and `tool_call` parts. |
| `agent_id` | string | no | Producing agent. Matches the Turn's `agent_id`. See [envelope.md §3.1](envelope.md#31-multi-agent-provenance). |
| `in_reply_to_call_id` | string | no | When the assistant Turn targets an in-flight dispatched call (e.g. interim status into its own outer call). Matches the Turn's `in_reply_to_call_id`. |

### 3.3 `crtx.turn.tool.called`

Convenience extraction of a `tool_call` ContentPart from an
assistant Turn. The same logical action MAY also surface inside the
preceding `crtx.turn.assistant.emitted` event's `content` array;
subscribers MUST tolerate seeing it via both paths (see §4).

Fields match [`ToolCallPart`](envelope.md#62-tool_call).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `envelope_id` | string | yes | |
| `turn_id` | string | yes | The assistant Turn that produced the call. |
| `call_id` | string | yes | Matches the responding `crtx.turn.tool.completed` event. |
| `name` | string | yes | Tool name. |
| `input` | object \| string | yes | Tool arguments. Object form canonical. |
| `parent_call_id` | string | no | Outer `call_id` whose execution issued this call. Same semantics as [`tool_call.parent_call_id`](envelope.md#62-tool_call). |
| `agent_id` | string | no | Producing agent. Matches the Turn's `agent_id`. |

### 3.4 `crtx.turn.tool.completed`

Emitted when a tool handler returns.

Fields match [`ToolResultPart`](envelope.md#63-tool_result).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `envelope_id` | string | yes | |
| `turn_id` | string | yes | The `tool`-role Turn carrying the result. |
| `call_id` | string | yes | Matches the originating `crtx.turn.tool.called`. |
| `output` | any | yes | JSON-serializable result. |
| `is_error` | boolean | no | Default `false`. When `true`, `output` SHOULD be a human-readable error description. |
| `child_envelope_id` | string | no | When the call ran out-of-band in a [dispatch nest](envelope.md#72-dispatch-nests), the child Envelope's id. Matches the `tool_result.child_envelope_id` field. |
| `agent_id` | string | no | Producing agent (the one that ran the tool or sub-agent and returned the result). Matches the Turn's `agent_id`. |

### 3.5 `crtx.turn.thinking.emitted`

Emitted when a model produces a reasoning trace (e.g. Claude
extended thinking). Consumers MAY drop these events without
violating spec conformance.

Fields match [`ThinkingPart`](envelope.md#65-thinking).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `envelope_id` | string | yes | |
| `turn_id` | string | yes | |
| `text` | string | yes | Reasoning trace. |
| `signature` | string | no | Provider-supplied signature for replay/verification. |
| `agent_id` | string | no | Producing agent. Matches the Turn's `agent_id`. |
| `in_reply_to_call_id` | string | no | When the thinking trace targets an in-flight dispatched call. Matches the Turn's `in_reply_to_call_id`. |

### 3.6 `crtx.turn.system.injected`

Emitted when the host runtime adds a `system`-role Turn (e.g.
initial system prompt, mid-conversation retraction, host-side
guardrail message).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `envelope_id` | string | yes | |
| `turn_id` | string | yes | |
| `content` | array of [ContentPart](envelope.md#6-contentpart) | yes | |
| `in_reply_to_call_id` | string | no | When the system Turn targets an in-flight dispatched call (e.g. host-runtime guardrail directed at a sub-agent). Matches the Turn's `in_reply_to_call_id`. |

### 3.7 `crtx.session.envelope.created`

Emitted when a new Envelope is materialized (before any Turns are
appended). Carries Envelope metadata only — no `turns`.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `envelope_id` | string | yes | The newly minted `Envelope.id`. |
| `created_at` | string (RFC 3339) | yes | Matches the Envelope's `created_at`. |
| `source` | [Source](envelope.md#5-source) | yes | Producing runtime. |
| `injected_turns` | array | no | Initial `Envelope.injected_turns` if seeded at creation. Matches [`InjectedTurnRef`](envelope.md#73-injected-turns). |

### 3.8 `crtx.session.envelope.forked`

Emitted when a what-if fork is created (see [envelope.md §7.1](envelope.md#71-what-if-forks)).
Distinct from `crtx.session.envelope.nested`: a fork inherits the
parent's Turns up to `fork_point`; a dispatch nest does not.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `parent_id` | string | yes | The parent Envelope's id. |
| `child_id` | string | yes | The child Envelope's id. |
| `fork_point` | integer | yes | Index into the parent's `turns` array at which the fork branched. |
| `created_at` | string (RFC 3339) | yes | When the child was materialized. |

### 3.9 `crtx.session.envelope.nested`

Emitted when a [dispatch nest](envelope.md#72-dispatch-nests) is
spawned: an open `tool_call` in the parent's transcript causes a
fresh child Envelope to materialize for the executor. The parent
producer emits this. The child also emits its own
`crtx.session.envelope.created`; the two events describe the same
moment from different perspectives.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `parent_id` | string | yes | The parent Envelope's id (the one containing the open `tool_call`). |
| `child_id` | string | yes | The dispatch-nest child Envelope's id. Matches `child.dispatched_from.envelope_id`'s referent. |
| `call_id` | string | yes | The open `tool_call.call_id` in the parent that spawned this nest. Matches `child.dispatched_from.call_id`. |
| `created_at` | string (RFC 3339) | yes | When the child was materialized. |

### 3.10 `crtx.session.envelope.returned`

Emitted when a dispatch-nest child's result has been folded back
into the parent Envelope as a `tool_result` Turn closing the open
`tool_call`. The parent producer emits this.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `parent_id` | string | yes | The parent Envelope's id. |
| `child_id` | string | yes | The dispatch-nest child's id (closed). |
| `call_id` | string | yes | The `tool_call.call_id` that has now been resolved. |
| `created_at` | string (RFC 3339) | yes | When the `tool_result` was appended to the parent. |
| `is_error` | boolean | no | Default `false`. Mirrors the parent-side `tool_result.is_error`. |

---

## 4. Ordering and atomicity

- Events are **best-effort delivery**. Subscribers MAY miss events.
  Authoritative state MUST be reconstructed from the
  [Envelope](envelope.md#2-envelope), never from the event stream
  alone.
- A `crtx.turn.assistant.emitted` event for a Turn that contains
  `tool_call` parts MAY be followed by one or more
  `crtx.turn.tool.called` events extracted from the same content.
  These are convenience events, not separate Turns.
- Subscribers MUST tolerate observing the same logical action via
  multiple topics (a `tool_call` appearing both inside a
  `crtx.turn.assistant.emitted` payload AND as a standalone
  `crtx.turn.tool.called` payload with the same `call_id`).
- Producers SHOULD emit events **after** the corresponding Turn has
  been persisted to the Envelope, so that a subscriber whose handler
  re-reads the Envelope does not race with the producer's append.
- Within a single conversation, producers SHOULD preserve emission
  order matching the canonical Turn order. Cross-topic ordering
  across the bus is the transport's concern.

---

## 5. Extensions

- Topics outside the `crtx.*` namespace are extensions. Implementations
  MUST use the form `x.<vendor>.<topic>` (reverse-DNS recommended:
  `x.io.jadb.custom.event`).
- Payloads for extension topics are caller-defined. This spec makes
  no claim on their shape.
- Subscribers encountering an extension topic SHOULD preserve unknown
  fields verbatim when forwarding the event, the same way envelope
  consumers preserve unknown ContentPart `type` values
  (see [envelope.md §6.6](envelope.md#66-extension-parts)).

---

## 6. What this taxonomy is NOT

- **Not a transport.** No requirement for Kafka, NATS, in-process
  channels, HTTP webhooks, or any specific bus. Any system with
  topic + payload semantics works.
- **Not a delivery guarantee.** Best-effort. Subscribers MUST
  reconstruct authoritative state from the Envelope, not from the
  event stream.
- **Not a session-replay protocol.** Events are observational;
  envelopes are authoritative. Replay tools consume envelopes.
- **Not a wire framing format.** Each transport wraps payloads in
  its own envelope (Kafka record, NATS message, HTTP body, etc.).
  The shapes defined here are the *payload contents*, not the
  transport frame.

---

## 7. Conformance

- A **producer** is v0.1-conformant if every topic it emits under
  `crtx.*` uses a canonical name from §3 AND every payload validates
  against the corresponding `$defs` entry in
  [`events.schema.json`](events.schema.json).
- A producer MAY emit any subset of canonical topics. A producer
  that emits only `crtx.turn.tool.called` is still conformant.
- A **subscriber** is v0.1-conformant if it tolerates missing
  optional fields and preserves unknown fields verbatim when
  forwarding payloads.
- The same versioning rule as
  [envelope.md §9](envelope.md#9-validation) applies: in case of
  conflict between schema and prose for a tagged release, **the
  schema wins**.
- Both envelopes and events declare the same `crtx_version: "0.1"`.
  A single spec version covers both surfaces.

---

## 8. Relationship to envelope

Events are observational; envelopes are authoritative. A complete
record of a conversation can be reconstructed from the Envelope
alone; events exist to accelerate live consumption (indexers,
dashboards, recorders).

---

## 9. Open questions for v0.1 → v0.2

- **Streaming partial events.** A `crtx.turn.assistant.delta` topic
  for chunked emission, or per-chunk wrappers around existing topics.
- **Cost / token usage events.** Likely
  `crtx.session.envelope.metered` carrying provider-reported counters.
- **Error topics.** A `crtx.error.*` family for producer-side
  failures (provider timeout, transport drop, schema validation
  reject) distinct from in-band `tool_result` errors.
- **Lifecycle terminators.** `crtx.session.envelope.closed`,
  `crtx.session.envelope.archived`, `crtx.session.envelope.retracted` —
  currently absent because v0.1 envelopes are open-ended by design.

These are deliberately out of scope for v0.1 to keep the canonical
topic list small while real implementations land.
