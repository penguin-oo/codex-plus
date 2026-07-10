# Mobile Interrupted Reply Recovery Design

## Goal

Make mobile conversations leave the replying state whenever Codex reaches a real terminal state, while preserving assistant text produced before an interrupted or failed turn. Quota percentages are display-only and never determine task completion.

## Current Failure

`CodexDataStore.load_messages` ignores non-final assistant messages and `event_msg/turn_aborted`, so interrupted output disappears after navigation or a backend restart. `JobRunner._run_codex_process` only treats a final answer as terminal; after any startup output there is no inactivity deadline, so an upstream terminal error can leave a job marked `running` indefinitely.

## Design

1. Track non-final assistant messages for the current turn while reading the persisted session JSONL.
2. If the turn ends through `event_msg/turn_aborted` or a subsequent user turn, expose the collected assistant messages as normal assistant history. At end-of-file, expose them only when `PortalService` has confirmed that the session has no active mobile job. Do not append an interruption reason or placeholder.
3. Keep completed turns unchanged: their final answer remains the durable assistant response and temporary progress text is not duplicated.
4. Parse structured Codex terminal events separately from quota snapshots. `turn.completed` and a turn-completed payload with status `completed` end successfully; `event_msg/turn_aborted`, explicit interrupted/failed turn status, and non-retryable terminal errors end unsuccessfully. `error` notifications with `willRetry=true` remain active. A structured `usageLimitExceeded` error is terminal, but a rate-limit snapshot or a displayed 100 percent value is not.
5. After a terminal event, allow the existing short process-exit grace period, then terminate a worker that remains alive. Mark jobs with a final answer as completed and jobs without one as failed or interrupted so Android stops polling.
6. Preserve the existing transient job error field for diagnostics, but do not inject error details into conversation history.

## Data Flow

`codex exec --json` output updates the in-memory job. Structured terminal events close the job independently of quota usage. The persisted Codex session JSONL remains the source of truth after navigation or restart. During an active mobile job, history reconstruction leaves the current incomplete tail to the live-job stream; after the job reaches a terminal state, it exposes that tail as durable mobile history.

## Testing

- An interrupted turn with assistant progress returns that progress and no synthetic reason.
- An interrupted turn with no assistant text adds no assistant message.
- A completed turn does not duplicate progress text before its final answer.
- A temporary end-of-file while a job is active does not expose progress as durable history.
- `turn.completed`, explicit failed/interrupted status, and non-retryable terminal errors end the process loop.
- A retryable error does not end the job.
- A rate-limit snapshot showing 100 percent does not end the job; an explicit terminal usage-limit error does.
