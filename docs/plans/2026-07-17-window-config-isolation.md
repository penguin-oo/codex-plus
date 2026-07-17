# Window Configuration Isolation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bind every desktop Codex terminal to a launch-time backend snapshot while preserving shared sessions, goals, skills, and safe OAuth behavior.

**Architecture:** Add a testable runtime-home module that creates lifecycle records and private Codex homes for non-auth providers. Refactor desktop command construction to pass one immutable settings snapshot through every launch step and wrap Codex execution with PID registration and safe cleanup.

**Tech Stack:** Python 3.11+, tkinter, pathlib, subprocess, unittest/pytest, Windows directory junctions, Codex CLI configuration overrides.

---

### Task 1: Runtime lifecycle tests

**Files:**
- Create: `tests/test_window_runtime.py`
- Create: `window_runtime.py`

**Step 1: Write failing tests**

Cover:

- an isolated runtime copies only the required snapshot files;
- `auth.json` is not copied;
- shared directories resolve to the original targets;
- explicit and baseline installation IDs are selected correctly;
- cleanup removes links and runtime files without deleting shared targets;
- a live or pending session lock blocks a second writable launch;
- dead runtime records are removed.

**Step 2: Verify the tests fail**

Run:

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n codex-accel python -m pytest tests/test_window_runtime.py -q
```

Expected: failure because `window_runtime` does not exist.

**Step 3: Implement the minimal runtime module**

Implement:

- `WindowRuntime`;
- `prepare_window_runtime`;
- `cleanup_window_runtime`;
- `cleanup_stale_window_runtimes`;
- safe runtime-root validation;
- one-batch Windows junction creation with a symlink fallback elsewhere;
- CLI cleanup entry point.

**Step 4: Verify the tests pass**

Run the same focused pytest command and expect all tests to pass.

### Task 2: PowerShell binding tests

**Files:**
- Modify: `tests/test_window_runtime.py`
- Modify: `window_runtime.py`

**Step 1: Write failing tests**

Require the generated PowerShell wrapper to:

- write the shell PID;
- set the per-window `CODEX_HOME`;
- point `CODEX_SQLITE_HOME` to the shared home;
- run cleanup in `finally`;
- avoid embedding installation IDs or API keys in runtime metadata.

**Step 2: Verify the tests fail**

Run the focused test module and confirm the missing wrapper behavior fails.

**Step 3: Implement the wrapper builder**

Add a pure `build_runtime_powershell_wrapper` function with PowerShell-safe
quoting and a cleanup helper command.

**Step 4: Verify the tests pass**

Run the focused tests again.

### Task 3: Desktop launch snapshot integration

**Files:**
- Modify: `app.py`
- Create: `tests/test_desktop_window_launch.py`

**Step 1: Write failing tests**

Assert that:

- backend argument generation accepts an explicit settings snapshot;
- proxy and API environment prefixes use that same snapshot;
- Codex Auth uses the shared home;
- token-pool and OpenAI-compatible modes use isolated runtime homes;
- a failed terminal launch immediately cleans its runtime;
- duplicate writable resume is reported instead of launched.

**Step 2: Verify the tests fail**

Run:

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n codex-accel python -m pytest tests/test_desktop_window_launch.py -q
```

**Step 3: Implement minimal app integration**

- Import `window_runtime`.
- Thread one copied settings mapping through backend readiness, argument
  generation, proxy selection, environment setup, and terminal command creation.
- Prepare the runtime after argument/model metadata setup.
- Wrap new and resumed Codex commands with the runtime PowerShell wrapper.
- Clean the runtime on launch failure.
- Run stale cleanup during the existing auto-refresh cycle.

**Step 4: Verify focused tests pass**

Run both new test modules.

### Task 4: Local behavior verification

**Files:**
- No production file changes unless verification exposes a defect.

**Step 1: Compile**

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n codex-accel python -m py_compile app.py window_runtime.py
```

**Step 2: Run the full Python suite**

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n codex-accel python -m pytest -q
```

**Step 3: Measure preparation latency**

Create and clean representative auth and OpenAI-compatible runtimes repeatedly.
Require the median preparation overhead to remain below 100 ms on this machine.

**Step 4: Verify Codex integration locally**

Use a loopback-only provider with a dummy key. Confirm:

- new session files appear in the shared sessions directory;
- SQLite state uses the shared home;
- the private installation ID is visible in request metadata;
- no external provider is contacted.

### Task 5: Integrate safely

**Files:**
- Review only the files changed by this feature.

**Step 1: Scan for secrets**

Search changed files for key, token, provider URL, machine ID, and private preset
patterns. Confirm no local value is present.

**Step 2: Commit the isolated feature**

Commit only:

- `app.py`;
- `window_runtime.py`;
- the new tests;
- the two plan documents.

**Step 3: Apply the feature commit to the main working tree**

Preserve all pre-existing mobile, Android, launcher, and APK changes. Resolve
only direct conflicts and rerun focused tests in the main workspace.

**Step 4: Report**

Report exact changed files, verification results, measured startup overhead, and
any remaining proxy-concurrency limitation. Do not push or synchronize unless
the user explicitly requests it.
