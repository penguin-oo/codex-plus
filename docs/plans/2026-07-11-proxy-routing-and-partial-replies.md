# Proxy Routing And Partial Replies Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separate network proxy routing from the local protocol adapter and keep partial assistant replies visible after any interruption.

**Architecture:** Protocol selection alone decides whether Codex uses the local `8317` adapter. The saved proxy preference continues to configure the outbound network environment. The Portal records user-visible assistant progress from live events and recovers it from rollout history when a job terminates before a final answer.

**Tech Stack:** Python 3 standard library and `unittest`, Android Java 17 and JUnit 4, Gradle 9.0.0.

---

### Task 1: Lock The Routing Contract

**Files:**
- Modify: `tests/test_app_helpers.py`
- Modify: `tests/test_mobile_portal.py`
- Modify: `app.py`
- Modify: `mobile_portal.py`

**Step 1: Write failing tests**

Assert that:

- `responses + proxy_preference=proxy` does not require the local adapter.
- `chat_completions` requires the adapter regardless of network preference.
- desktop and Portal launch overrides retain the upstream Base URL for
  Responses presets.

**Step 2: Run tests and verify the regression**

Run:

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n codex-accel python -m unittest tests.test_app_helpers tests.test_mobile_portal -v
```

Expected: the Responses proxy-preference assertions fail because the current
helpers return `True` and select `127.0.0.1:8317`.

**Step 3: Implement the minimal routing change**

Make the local-adapter predicates depend only on
`OPENAI_PROTOCOL_CHAT_COMPLETIONS`. Leave network environment generation based
on `proxy_preference`.

**Step 4: Re-run focused tests**

Expected: all routing tests pass.

### Task 2: Capture User-Visible Live Assistant Progress

**Files:**
- Modify: `tests/test_mobile_portal_job_state.py`
- Modify: `mobile_portal.py`

**Step 1: Write failing tests**

Cover an `event_msg` whose payload is:

```python
{
    "type": "agent_message",
    "message": "partial reply",
    "phase": "commentary",
}
```

Assert that the job receives `live_text` and `last_message`.

**Step 2: Verify the test fails**

Run:

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n codex-accel python -m unittest tests.test_mobile_portal_job_state -v
```

Expected: `live_text` remains unchanged because `_extract_event_text` ignores
the payload `message` field.

**Step 3: Implement event extraction**

Accept `message` only from user-visible `agent_message` event payloads. Keep
error, reasoning, and tool events excluded.

**Step 4: Re-run focused tests**

Expected: all job-state tests pass.

### Task 3: Recover Partial Text At Termination

**Files:**
- Modify: `tests/test_mobile_portal_job_state.py`
- Modify: `tests/test_mobile_portal_messages.py`
- Modify: `mobile_portal.py`

**Step 1: Write failing tests**

Assert that:

- manual cancellation falls back to assistant progress in the rollout when
  `live_text` is empty;
- failed/stale recovery uses the same fallback;
- `load_messages` includes commentary from an aborted turn;
- a completed final answer suppresses commentary fallback and is not
  duplicated.

**Step 2: Verify tests fail**

Run the new focused unittest modules and confirm the missing partial text
assertions fail.

**Step 3: Implement rollout recovery**

Add a data-store helper that scans only the current turn since a supplied
timestamp, tracks user-visible `agent_message` text, and returns it only when
the turn has no final answer. Use it in cancellation and terminal recovery,
and align `load_messages` with the same rule.

**Step 4: Re-run focused tests**

Expected: cancellation, stale recovery, aborted history, and completed-history
tests pass.

### Task 4: Verify Android Terminal Rendering

**Files:**
- Modify: `android-app/app/src/test/java/com/penguinoo/codexmobile/ChatWatchStateTest.java`
- Modify only if required: `android-app/app/src/main/java/com/penguinoo/codexmobile/ChatActivity.java`

**Step 1: Extend the Android regression test**

Assert that a cancelled or failed `PortalJob` retains its partial reply through
`ChatStreamingState.resolveLiveText` and produces the stable interruption
notice where appropriate.

**Step 2: Run Android unit tests**

```powershell
$env:ANDROID_HOME='C:\Users\MECHREVO\AppData\Local\Android\Sdk'
$env:ANDROID_SDK_ROOT=$env:ANDROID_HOME
& 'C:\Users\MECHREVO\.gradle\wrapper\dists\gradle-9.0.0-bin\d6wjpkvcgsg3oed0qlfss3wgl\gradle-9.0.0\bin\gradle.bat' :app:testDebugUnitTest --console=plain
```

If the test exposes a presentation gap, make the smallest Android change and
run it again.

### Task 5: Full Verification And Packaging

**Files:**
- Update: `app/CodexPlus-debug.apk`

**Step 1: Run Python verification**

Run syntax checks and the complete Python test suite under `codex-accel`.

**Step 2: Run Android verification**

Run `:app:testDebugUnitTest` and `:app:assembleDebug`.

**Step 3: Update the packaged APK**

Copy the verified output from
`android-app/app/build/outputs/apk/debug/app-debug.apk` to
`app/CodexPlus-debug.apk`.

**Step 4: Inspect the final diff**

Run `git diff --check`, scan added lines for credential patterns and private
configuration, and confirm no local settings files are tracked.
