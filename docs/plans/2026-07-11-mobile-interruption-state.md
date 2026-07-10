# Mobile Interruption State Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure interrupted mobile Codex jobs leave `replying`, retain partial assistant text, and display a stable interruption notice without stopping based on quota percentages.

**Architecture:** Keep job termination authoritative in `mobile_portal.py`: transient errors remain running, while process exit, stale-process recovery, or missing final output produces a retained `failed` job. Android continues to render `live_text`, but treats a terminal failed job or an exhausted polling watch as interrupted and clears its local replying controls.

**Tech Stack:** Python 3 standard library, Android Java 17, JUnit 4, Gradle 9.0.0.

---

### Task 1: Reproduce stale-job loss in the backend

**Files:**
- Create: `tests/test_mobile_portal_job_state.py`
- Modify: `mobile_portal.py:2705-3503`

**Step 1: Write the failing test**

Create a `unittest` test with a minimal fake data store. Insert a `running` job whose PID is dead and heartbeat is older than `RUNNING_JOB_GRACE_SECONDS`, call `_recover_stale_session_locked`, and assert that the job remains present with:

```python
assert job["status"] == "failed"
assert job["live_text"] == "partial reply"
assert job["error"] == "Reply interrupted. The response may be incomplete."
```

**Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n codex-accel python -m unittest tests.test_mobile_portal_job_state.MobileJobStateTests.test_dead_stale_job_is_retained_as_failed -v
```

Expected: FAIL because the current stale recovery deletes the job.

**Step 3: Implement the minimal backend state change**

Add a generic interruption constant and change `_recover_stale_session_locked` to retain the job, preserve `live_text`/`last_message`, clear the PID, set `finished_at`, mark `failed`, and remove only the session from `active_sessions`.

**Step 4: Run test to verify it passes**

Run the same unittest command. Expected: PASS.

### Task 2: Preserve runtime diagnostics without premature quota stopping

**Files:**
- Modify: `tests/test_mobile_portal_job_state.py`
- Modify: `mobile_portal.py:3034-3415`

**Step 1: Write failing tests**

Add tests asserting:

- A top-level Codex `error` event records diagnostic text but leaves the job `running`.
- A `token_count` event with `used_percent: 100` leaves the job `running` and records no terminal error.
- Finishing a failed job exposes the generic interruption text while retaining the detailed diagnostic in an internal field.

**Step 2: Run tests to verify failure**

Run:

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n codex-accel python -m unittest tests.test_mobile_portal_job_state -v
```

Expected: the error-event and diagnostic assertions fail before implementation.

**Step 3: Implement minimal event handling**

- Capture top-level `error` messages as `diagnostic_error` without changing status.
- Keep reconnecting and quota telemetry non-terminal.
- When `_run_codex_process` finally exits unsuccessfully or without a final answer, finish the job as `failed`, expose the generic interruption message, and preserve the diagnostic separately.

**Step 4: Run tests to verify pass**

Run the full backend unittest file. Expected: PASS.

### Task 3: Make Android clear replying after terminal or lost watches

**Files:**
- Create: `android-app/app/src/test/java/com/penguinoo/codexmobile/ChatWatchStateTest.java`
- Modify: `android-app/app/src/main/java/com/penguinoo/codexmobile/ChatWatchState.java`
- Modify: `android-app/app/src/main/java/com/penguinoo/codexmobile/ChatActivity.java:541-649`
- Modify: `android-app/app/src/main/res/values/strings.xml`

**Step 1: Write failing Java tests**

Test that the watch-state helper returns the stable interruption notice for failed or unavailable jobs while preserving partial text through `ChatStreamingState.resolveLiveText`.

**Step 2: Run tests to verify failure**

Run from `android-app`:

```powershell
$env:ANDROID_HOME='C:\Users\MECHREVO\AppData\Local\Android\Sdk'
$env:ANDROID_SDK_ROOT=$env:ANDROID_HOME
& 'C:\Users\MECHREVO\.gradle\wrapper\dists\gradle-9.0.0-bin\d6wjpkvcgsg3oed0qlfss3wgl\gradle-9.0.0\bin\gradle.bat' :app:testDebugUnitTest --console=plain
```

Expected: FAIL because the stable interruption helper does not exist.

**Step 3: Implement Android terminal handling**

- Use one generic interruption string resource.
- On a failed job, clear `attachedJobId` and `watchingJobId`, render retained partial text as non-ephemeral, restore the composer when the lease is still valid, and set a persistent interruption banner.
- After repeated polling failures, perform the same local interruption transition instead of leaving the stop/replying state active.
- Do not alter behavior for transient polling failures before the retry threshold.

**Step 4: Run unit tests to verify pass**

Run `:app:testDebugUnitTest` again. Expected: PASS.

### Task 4: Build and verify the packaged app

**Files:**
- Update: `app/CodexPlus-debug.apk`

**Step 1: Run Python syntax and unit verification**

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n codex-accel python -m py_compile mobile_portal.py
conda run -n codex-accel python -m unittest tests.test_mobile_portal_job_state -v
```

Expected: all commands succeed.

**Step 2: Build Android APK**

From `android-app` run Gradle 9.0.0 `:app:assembleDebug --console=plain` with the configured Android SDK variables.

Expected output: `android-app/app/build/outputs/apk/debug/app-debug.apk`.

**Step 3: Replace packaged APK**

Copy the verified debug APK to `app/CodexPlus-debug.apk`.

**Step 4: Scan for sensitive additions and inspect diff**

Run targeted searches for key/token/private URL patterns in added lines, `git diff --check`, and `git status --short --branch`.

Expected: no sensitive local configuration appears in tracked changes.

**Step 5: Commit implementation**

```powershell
git add mobile_portal.py tests/test_mobile_portal_job_state.py android-app/app/src/main/java/com/penguinoo/codexmobile/ChatWatchState.java android-app/app/src/main/java/com/penguinoo/codexmobile/ChatActivity.java android-app/app/src/main/res/values/strings.xml android-app/app/src/test/java/com/penguinoo/codexmobile/ChatWatchStateTest.java app/CodexPlus-debug.apk docs/plans/2026-07-11-mobile-interruption-state.md
git commit -m "Fix mobile interrupted reply state"
```
