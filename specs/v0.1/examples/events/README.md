# crtx v0.1 — event payload examples

Each file is a single concrete payload that validates against the
corresponding `$defs` entry in [`../../events.schema.json`](../../events.schema.json).
Topic names follow the canonical
`crtx.<category>.<object>.<action>` convention defined in
[`../../events.md`](../../events.md).

| File | Topic | Schema `$defs` entry |
|------|-------|----------------------|
| [`user_received.json`](user_received.json) | `crtx.turn.user.received` | `UserReceivedPayload` |
| [`assistant_emitted.json`](assistant_emitted.json) | `crtx.turn.assistant.emitted` | `AssistantEmittedPayload` |
| [`tool_called.json`](tool_called.json) | `crtx.turn.tool.called` | `ToolCalledPayload` |
| [`tool_completed.json`](tool_completed.json) | `crtx.turn.tool.completed` | `ToolCompletedPayload` |
| [`thinking_emitted.json`](thinking_emitted.json) | `crtx.turn.thinking.emitted` | `ThinkingEmittedPayload` |
| [`session_created.json`](session_created.json) | `crtx.session.envelope.created` | `SessionCreatedPayload` |
| [`session_forked.json`](session_forked.json) | `crtx.session.envelope.forked` | `SessionForkedPayload` |
| [`session_nested.json`](session_nested.json) | `crtx.session.envelope.nested` | `SessionNestedPayload` |
| [`session_returned.json`](session_returned.json) | `crtx.session.envelope.returned` | `SessionReturnedPayload` |

The `envelope_id` / `turn_id` values in `user_received.json`,
`assistant_emitted.json`, `tool_called.json`, and
`tool_completed.json` deliberately reuse the ids from
[`../tool-call.json`](../tool-call.json) so the sequence of events
maps 1:1 onto that envelope. The `session_created.json` example
points at the same envelope; `session_forked.json` mirrors
[`../fork.json`](../fork.json); `session_nested.json` and
`session_returned.json` mirror [`../dispatch-nested.json`](../dispatch-nested.json).

`crtx.turn.assistant.emitted`, `crtx.turn.tool.called`,
`crtx.turn.tool.completed`, and `crtx.turn.thinking.emitted`
payloads MAY carry an optional `agent_id`;
`crtx.turn.tool.called` MAY also carry `parent_call_id` for
in-band nested dispatch; `crtx.turn.tool.completed` MAY carry
`child_envelope_id` when the call ran in an out-of-band dispatch
nest. See [`../../envelope.md` §3.1](../../envelope.md#31-multi-agent-provenance),
[§6.2](../../envelope.md#62-tool_call), and [§7.2](../../envelope.md#72-dispatch-nests).

`crtx.turn.user.received`, `crtx.turn.assistant.emitted`,
`crtx.turn.thinking.emitted`, and `crtx.turn.system.injected`
payloads MAY carry an optional `in_reply_to_call_id` for mid-flight
messaging into an open dispatched call. See
[`../../envelope.md` §3.2](../../envelope.md#32-mid-flight-messaging).

`crtx.session.envelope.created` MAY carry `injected_turns` when the
Envelope is seeded with foreign Turn slices at creation. See
[`../../envelope.md` §7.3](../../envelope.md#73-injected-turns).
[`../injection.json`](../injection.json) shows mid-session
injection (append-only entries with `injected_after_turn_id`).

The event sequences for [`../dispatch.json`](../dispatch.json),
[`../dispatch-nested.json`](../dispatch-nested.json), and
[`../injection.json`](../injection.json) exercise the full surface.
