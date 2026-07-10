# Mobile Interruption State Design

## Goal

When a mobile-controlled Codex job stops without a complete final answer, the phone must stop showing `replying`, retain any partial assistant text, restore the composer, and show a persistent generic interruption notice.

Quota percentage displays are informational only. A displayed value of 100% must never stop a job by itself.

## State Rules

- `running`: the Codex process is alive or is still performing its own transient reconnect/retry flow.
- `completed`: a final assistant answer was observed.
- `cancelled`: the user explicitly stopped the job.
- `failed`: the process exited, disappeared, or ended without a final assistant answer.

Transient connection errors do not immediately change `running` to `failed`. The final process outcome decides the terminal state.

## Backend Behavior

- Preserve `live_text` and `last_message` when a job fails.
- Capture runtime error events as diagnostic context, but expose a stable generic interruption message to the mobile UI.
- When stale-job recovery finds a dead process with no final answer, retain the job and mark it `failed` instead of deleting it.
- Never infer failure from quota usage percentages.

## Android Behavior

- Stop the watcher when a terminal job state is received.
- Clear the session's `replying` state and re-enable the composer.
- Render retained partial assistant text as non-ephemeral content.
- Show a persistent interruption notice: `Reply interrupted. The response may be incomplete.`
- Reopening the conversation must show the latest failed job's retained partial text and interruption state.

## Verification

- A dead stale process becomes `failed` and remains queryable.
- A failed job retains partial text.
- A transient reconnect remains `running`.
- A completed final answer remains `completed`.
- Android clears `replying`, preserves partial text, and shows the interruption notice for failed jobs.
- Quota percentages do not participate in terminal-state decisions.
