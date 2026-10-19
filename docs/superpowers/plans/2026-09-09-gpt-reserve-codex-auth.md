# GPT Reserve Codex Auth Model Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the account-scoped `gpt-reserve` model only for official Codex Auth launches in the desktop and mobile chat manager.

**Architecture:** Keep the reserve model separate from generic fallback and API-provider catalogs. Add it only when building Codex Auth model choices; reuse the existing desktop and mobile launch argument builders, which already pass the selected model with `-m`. No quota, auth, proxy, or retry behavior changes.

**Tech Stack:** Python 3, unittest/pytest, Tkinter desktop UI, embedded mobile portal UI.

---

## Chunk 1: Model Catalog Helpers

### Task 1: Add failing catalog tests

**Files:**
- Modify: `tests/test_context_window.py` or `tests/test_proxy_routing.py`
- Modify: `app.py`
- Modify: `mobile_portal.py`

- [x] Add tests proving the official-auth catalog includes `gpt-reserve`.
- [x] Add tests proving OpenAI-compatible and token-pool fallback catalogs do not include `gpt-reserve`.
- [x] Run the focused tests and confirm they fail before implementation.

### Task 2: Implement scoped model catalogs

**Files:**
- Modify: `app.py:91-100, 1564-1573, 2348-2376`
- Modify: `mobile_portal.py:79-89, 1981-2002, 2758-2797`

- [x] Define the shared reserve model identifier as `gpt-reserve` without adding it to generic API fallback constants.
- [x] Add an explicit Codex Auth catalog path that appends `gpt-reserve` once.
- [x] Keep OpenAI-compatible preset and token-pool catalogs unchanged.
- [x] Run the focused catalog tests and confirm they pass.

## Chunk 2: CLI Launch Wiring

### Task 3: Add failing launch-argument tests

**Files:**
- Modify: `tests/test_context_window.py`
- Modify: `tests/test_desktop_window_launch.py`

- [x] Add a desktop test that selecting `gpt-reserve` produces `-m gpt-reserve` for a Codex Auth new chat.
- [x] Add mobile new-chat and resume tests that produce `-m gpt-reserve` under Codex Auth.
- [x] Confirm the tests fail if the model is not present in the catalog or is replaced by a default.

### Task 4: Implement and preserve routing boundaries

**Files:**
- Modify: `app.py:2621-2762`
- Modify: `mobile_portal.py:570-676`

- [x] Ensure Codex Auth selection passes `gpt-reserve` unchanged to the existing CLI argument path.
- [x] Ensure API-compatible paths do not route `gpt-reserve` through their provider proxy.
- [x] Run focused launch tests and confirm they pass.

### Task 5: Keep Reserve Visible Inside Interactive Chats

**Files:**
- Modify: `token_pool_settings.py`
- Modify: `app.py`
- Modify: `mobile_portal.py`
- Modify: `tests/test_context_window.py`

- [x] Generate a Codex Auth-only static model catalog with `gpt-reserve` marked `list`.
- [x] Pass the catalog with `model_catalog_json` for desktop and mobile launches.
- [x] Verify the installed CLI model catalog exposes `gpt-reserve` after cache refresh behavior.

## Chunk 3: Regression Verification

**Files:**
- Verify only.

- [x] Run the full test suite with `python -m pytest -p no:cacheprovider -q`.
- [x] Run Python compilation for changed modules.
- [x] Parse the embedded mobile JavaScript.
- [x] Run `git diff --check`.
- [x] Review the diff to ensure existing unrelated deletions and backups remain untouched.
