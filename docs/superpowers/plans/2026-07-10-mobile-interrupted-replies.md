# Mobile Interrupted Reply Recovery Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop mobile replying state on real Codex terminal events and preserve assistant text generated before an interrupted turn without adding interruption reasons.

**Architecture:** Keep Codex session JSONL as durable history and the in-memory job as the live source. Message parsing accepts an explicit `include_incomplete_tail` decision from `PortalService`, while a pure terminal-event classifier drives `JobRunner` independently of quota display percentages.

**Tech Stack:** Python 3 standard library, `unittest`/`pytest`, Codex JSONL event stream.

---

## Chunk 1: Durable Interrupted Output

### Task 1: Preserve interrupted assistant progress

**Files:**
- Create: `tests/test_mobile_reply_terminal_state.py`
- Modify: `mobile_portal.py:2249`
- Modify: `mobile_portal.py:2551`
- Modify: `mobile_portal.py:4206`

- [ ] **Step 1: Write failing message-history tests**

Create temporary history/session JSONL fixtures and assert:

```python
def test_turn_aborted_preserves_progress_without_reason():
    messages = load_fixture_messages(include_incomplete_tail=False)
    assert messages[-1]["text"] == "partial assistant text"
    assert "interrupted" not in messages[-1]["text"].lower()

def test_active_incomplete_tail_is_not_persisted():
    messages = load_fixture_messages(include_incomplete_tail=False, terminal_event=None)
    assert all(item["text"] != "partial assistant text" for item in messages)

def test_inactive_incomplete_tail_is_preserved():
    messages = load_fixture_messages(include_incomplete_tail=True, terminal_event=None)
    assert messages[-1]["text"] == "partial assistant text"

def test_completed_turn_uses_only_final_answer():
    messages = load_completed_fixture_messages()
    assert [item["text"] for item in messages if item["role"] == "assistant"] == ["final answer"]
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_mobile_reply_terminal_state.py -k "progress or incomplete or completed" -q`

Expected: FAIL because `load_messages` has no `include_incomplete_tail` behavior and discards interrupted progress.

- [ ] **Step 3: Implement minimal history parsing changes**

Update `CodexDataStore.load_messages(session_id, include_incomplete_tail=False)` to collect non-final assistant message entries for the current turn. Flush those entries only on `event_msg/turn_aborted`, when a later user turn starts, or at EOF when `include_incomplete_tail` is true. Discard them when a final answer exists.

Thread the flag through `CodexDataStore.session_payload`. In `PortalService.session_payload`, resolve the active job first and pass `include_incomplete_tail=active_job is None`.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_mobile_reply_terminal_state.py -k "progress or incomplete or completed" -q`

Expected: PASS.

## Chunk 2: Real Terminal-State Convergence

### Task 2: Classify terminal events without quota-percentage heuristics

**Files:**
- Modify: `tests/test_mobile_reply_terminal_state.py`
- Modify: `mobile_portal.py:3250`
- Modify: `mobile_portal.py:3358`

- [ ] **Step 1: Write failing event-classification tests**

Define the desired pure helper contract:

```python
assert classify_codex_terminal_event({"type": "turn.completed"}) == ("completed", "")
assert classify_codex_terminal_event({"type": "event_msg", "payload": {"type": "turn_aborted"}})[0] == "interrupted"
assert classify_codex_terminal_event({"type": "error", "willRetry": True, "error": {"message": "temporary"}}) == ("", "")
assert classify_codex_terminal_event({"type": "error", "willRetry": False, "error": {"message": "failed"}}) == ("failed", "failed")
assert classify_codex_terminal_event({"type": "account.rateLimits.updated", "usedPercent": 100}) == ("", "")
assert classify_codex_terminal_event({"type": "error", "error": {"codexErrorInfo": "usageLimitExceeded", "message": "limit"}})[0] == "failed"
```

Also cover `turn/completed` payloads whose turn status is `completed`, `interrupted`, or `failed`.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_mobile_reply_terminal_state.py -k "terminal or quota or retry" -q`

Expected: FAIL because the classifier does not exist.

- [ ] **Step 3: Implement the pure classifier**

Add `classify_codex_terminal_event(event) -> tuple[str, str]`. It must inspect explicit event names/status fields and retry metadata only. It must never inspect `usedPercent`, quota summaries, or other display data.

- [ ] **Step 4: Integrate classifier into the process loop**

Change `_handle_codex_event` to return detected session ID plus terminal status/error. Mark final assistant items as `has_final_answer`, but use explicit terminal events to start the existing process-exit grace period. After the grace period, stop a worker that remains alive. Return success only for a completed turn with a final answer; raise the captured terminal error or a generic empty-completion error otherwise so `_finish_job` releases `active_sessions`.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `python -m pytest tests/test_mobile_reply_terminal_state.py -q`

Expected: PASS.

## Chunk 3: Regression Verification

### Task 3: Verify backend behavior and startup

**Files:**
- Modify only if a regression is found: `mobile_portal.py`

- [ ] **Step 1: Run syntax checks**

Run: `python -m py_compile mobile_portal.py`

Expected: exit code 0.

- [ ] **Step 2: Run all available Python tests**

Run: `python -m pytest -q`

Expected: PASS.

- [ ] **Step 3: Start the mobile backend and verify API health**

Start the existing `mobile_portal.py`, request the local bootstrap/session API with the configured token, and confirm port `8765` responds. No Android source change or APK rebuild is required.

- [ ] **Step 4: Review the final diff**

Run: `git diff --check`

Expected: no whitespace errors.
