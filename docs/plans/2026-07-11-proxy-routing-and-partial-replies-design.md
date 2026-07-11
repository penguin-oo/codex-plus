# Proxy Routing And Partial Replies Design

## Goal

Restore the intended separation between the optional network proxy and the
local protocol adapter, and preserve partial assistant replies whenever a
mobile-visible Codex turn is interrupted.

## Routing Rules

- `proxy_preference` controls only the network proxy environment used to reach
  an upstream API.
- An OpenAI-compatible preset using `responses` connects Codex directly to the
  configured upstream Base URL.
- An OpenAI-compatible preset using `chat_completions` connects Codex to the
  local adapter on port `8317`, which translates Codex Responses requests for
  the upstream API.
- The local adapter inherits or receives the selected upstream network proxy
  independently of the protocol decision.

## Partial Reply Rules

- Live Codex `agent_message` events contribute text to the running job even
  when their phase is commentary rather than `final_answer`.
- Cancelling or failing a job preserves the latest live assistant text.
- If live job state has no text, the backend recovers assistant progress from
  the session rollout written since the job started.
- A session whose latest turn was aborted exposes its assistant progress in
  normal message history without duplicating completed final answers.
- Android renders retained interruption text as a non-ephemeral assistant
  message, clears the replying state, restores the composer, and keeps the
  interruption notice visible.

## Error Handling

- A missing or unreadable rollout file does not block cancellation.
- Recovery never substitutes reasoning or tool output for user-visible
  assistant messages.
- Network proxy selection does not start the local protocol adapter.
- Quota telemetry remains informational and does not terminate a job.

## Verification

- Desktop and Portal helper tests assert that `responses + proxy` uses the
  upstream Base URL while `chat_completions` uses `127.0.0.1:8317`.
- Tests assert that the network proxy environment is still enabled for a
  `proxy` preset.
- Backend tests cover live `agent_message` extraction, manual cancellation,
  stale failure recovery, and aborted rollout history.
- Android unit tests cover retained partial text and terminal interruption
  presentation.
- The Python suite, Android unit tests, and debug APK build must pass.
