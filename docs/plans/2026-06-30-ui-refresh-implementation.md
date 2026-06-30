# UI Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refresh the desktop, mobile web, and Android UI while preserving all existing Codex session-manager behavior.

**Architecture:** Keep the current architecture: Tkinter/ttk in `app.py`, inline mobile portal HTML/CSS/JS in `mobile_portal.py`, and Android AppCompat XML/ViewBinding under `android-app`. Treat this as a visual-system and layout pass, not a feature rewrite.

**Tech Stack:** Python 3.11, Tkinter/ttk, stdlib HTTP mobile portal, HTML/CSS/JS, Android XML resources, AppCompat, Gradle 9.0.0.

---

### Task 1: Protect The Baseline

**Files:**
- Inspect: `app.py`
- Inspect: `mobile_portal.py`
- Inspect: `android-app/app/src/main/res/values/colors.xml`
- Inspect: `android-app/app/src/main/res/values/themes.xml`
- Inspect: `android-app/app/src/main/res/layout/*.xml`
- Inspect: `android-app/app/src/main/res/drawable/*.xml`

**Step 1: Confirm worktree state**

Run:

```powershell
git status --short --branch
```

Expected: existing non-UI modified files may remain; do not revert them.

**Step 2: Run baseline Python checks**

Run:

```powershell
$env:PYTHONNOUSERSITE='1'; conda run -n codex-accel python -m py_compile app.py mobile_portal.py custom_provider_proxy.py token_pool_proxy.py token_pool_settings.py process_singleton.py
$env:PYTHONNOUSERSITE='1'; conda run -n codex-accel python -m pytest tests
```

Expected: compile succeeds and tests pass.

### Task 2: Add Style-Safety Tests For Mobile Web

**Files:**
- Modify: `tests/test_mobile_portal.py`
- Modify later: `mobile_portal.py`

**Step 1: Write failing tests**

Add tests that parse `mobile_portal.INDEX_HTML` and assert the refreshed UI contract:

```python
def test_mobile_portal_uses_operational_shell_not_hero_card(self):
    html = mobile_portal.INDEX_HTML
    self.assertIn('class="app-shell"', html)
    self.assertIn('class="workspace-panel"', html)
    self.assertIn('class="conversation-panel"', html)
    self.assertNotIn('radial-gradient(circle at top left', html)

def test_mobile_portal_keeps_required_controls_after_refresh(self):
    html = mobile_portal.INDEX_HTML
    for element_id in [
        "sessionList",
        "openNewChat",
        "backendModeSelect",
        "messageList",
        "promptInput",
        "sendPrompt",
        "newChatModal",
    ]:
        self.assertIn(f'id="{element_id}"', html)
```

**Step 2: Verify RED**

Run:

```powershell
$env:PYTHONNOUSERSITE='1'; conda run -n codex-accel python -m pytest tests/test_mobile_portal.py -k "mobile_portal_uses_operational_shell_not_hero_card or mobile_portal_keeps_required_controls_after_refresh" -v
```

Expected: the shell class test fails because the refreshed class names do not exist yet.

### Task 3: Refresh Mobile Web CSS And Layout

**Files:**
- Modify: `mobile_portal.py:4195-4495`
- Test: `tests/test_mobile_portal.py`

**Step 1: Implement refreshed shell**

Update `INDEX_HTML` so the outer shell uses:

- `app-shell` for the page container
- `topbar` for compact title/status
- `workspace-layout` for the two-column desktop layout
- `workspace-panel` for left navigation/list/settings
- `conversation-panel` for selected session/chat

Keep all existing IDs, API calls, event handlers, tab buttons, modals, and form controls.

**Step 2: Replace visual tokens**

Use a neutral dark palette:

```css
--bg: #0b0d10;
--surface: #111418;
--surface-2: #171b20;
--surface-3: #1d2329;
--line: rgba(219, 226, 234, 0.12);
--text: #eef2f6;
--muted: #98a2ad;
--accent: #44c2a8;
--danger: #f97066;
--radius: 10px;
```

Remove radial decorative background gradients and reduce large shadows.

**Step 3: Verify GREEN**

Run the tests from Task 2. Expected: pass.

### Task 4: Add Desktop UI Style Tests

**Files:**
- Modify: `tests/test_app_helpers.py`
- Modify later: `app.py`

**Step 1: Write failing test**

Add a source-level test for the desktop UI style contract:

```python
def test_desktop_ui_declares_refreshed_ttk_styles(self):
    source = Path(app.__file__).read_text(encoding="utf-8")
    self.assertIn("Toolbar.TFrame", source)
    self.assertIn("Primary.TButton", source)
    self.assertIn("Inspector.TLabelframe", source)
    self.assertIn("#f8fafc", source)
```

**Step 2: Verify RED**

Run:

```powershell
$env:PYTHONNOUSERSITE='1'; conda run -n codex-accel python -m pytest tests/test_app_helpers.py -k desktop_ui_declares_refreshed_ttk_styles -v
```

Expected: fails until desktop styles are added.

### Task 5: Refresh Desktop Tkinter UI

**Files:**
- Modify: `app.py:1311-1570`
- Test: `tests/test_app_helpers.py`

**Step 1: Add ttk style setup**

In `_build_ui` or a nearby helper, configure:

- root background `#f8fafc`
- toolbar frame style
- primary/danger/secondary button styles where supported by the active ttk theme
- Treeview header, row, selection, and alternating tags
- inspector labelframe styling for details/MCP/skills

**Step 2: Adjust layout density**

Group primary actions first, secondary actions next, and account/status on the right. Keep button commands unchanged.

**Step 3: Verify GREEN**

Run the Task 4 test. Expected: pass.

### Task 6: Add Android Resource Contract Tests

**Files:**
- Modify: `android-app/app/src/test/java/com/penguinoo/codexmobile/`
- Modify later: Android XML resources

**Step 1: Add resource text tests if local test structure supports XML file reads**

Create a focused JVM test that reads resource files and asserts:

- `colors.xml` contains `#0B0D10` or equivalent neutral app background.
- `bg_card.xml` radius is no more than `12dp`.
- `bg_panel.xml` radius is no more than `14dp`.

If Android JVM tests cannot reliably read raw resource files, skip this task and verify through Gradle build plus source inspection.

**Step 2: Verify RED**

Run:

```powershell
cd android-app
$env:ANDROID_HOME='C:\Users\MECHREVO\AppData\Local\Android\Sdk'
$env:ANDROID_SDK_ROOT='C:\Users\MECHREVO\AppData\Local\Android\Sdk'
& 'C:\Users\MECHREVO\.gradle\wrapper\dists\gradle-9.0.0-bin\d6wjpkvcgsg3oed0qlfss3wgl\gradle-9.0.0\bin\gradle.bat' :app:testDebugUnitTest --console=plain
```

Expected: new contract test fails until resources are updated, or task is explicitly skipped with reason.

### Task 7: Refresh Android Theme And Layout Resources

**Files:**
- Modify: `android-app/app/src/main/res/values/colors.xml`
- Modify: `android-app/app/src/main/res/values/themes.xml`
- Modify: `android-app/app/src/main/res/drawable/bg_card.xml`
- Modify: `android-app/app/src/main/res/drawable/bg_card_active.xml`
- Modify: `android-app/app/src/main/res/drawable/bg_panel.xml`
- Modify: `android-app/app/src/main/res/drawable/bg_home_action.xml`
- Modify: `android-app/app/src/main/res/drawable/bg_user_bubble.xml`
- Modify: `android-app/app/src/main/res/drawable/bg_assistant_bubble.xml`
- Modify: `android-app/app/src/main/res/layout/activity_main.xml`
- Modify: `android-app/app/src/main/res/layout/activity_chat.xml`
- Modify: `android-app/app/src/main/res/layout/activity_new_chat.xml`
- Modify: `android-app/app/src/main/res/layout/item_session.xml`

**Step 1: Update resources**

Replace the deep-blue palette with the shared neutral dark palette, keep accent and danger colors meaningful, and reduce panel/card radii.

**Step 2: Tighten layouts**

Reduce repeated card stacking on home and new chat screens. Keep touch targets at least 44dp. Keep all existing view IDs.

**Step 3: Verify Android build**

Run:

```powershell
cd android-app
$env:ANDROID_HOME='C:\Users\MECHREVO\AppData\Local\Android\Sdk'
$env:ANDROID_SDK_ROOT='C:\Users\MECHREVO\AppData\Local\Android\Sdk'
& 'C:\Users\MECHREVO\.gradle\wrapper\dists\gradle-9.0.0-bin\d6wjpkvcgsg3oed0qlfss3wgl\gradle-9.0.0\bin\gradle.bat' :app:assembleDebug --console=plain
```

Expected: debug APK builds successfully.

### Task 8: Visual Verification

**Files:**
- Inspect runtime UI only

**Step 1: Desktop visual check**

Launch:

```powershell
$env:PYTHONNOUSERSITE='1'; conda run -n codex-accel python app.py
```

Inspect toolbar grouping, launch options, session table, details tabs, zoom behavior, and text fit.

**Step 2: Mobile web visual check**

Launch:

```powershell
run-mobile.bat
```

Open the printed localhost URL with token. Check desktop browser width and phone-width responsive layout.

**Step 3: Android output check**

Confirm:

```text
android-app\app\build\outputs\apk\debug\app-debug.apk
```

exists after build. If an emulator/device is available, inspect main, all chats, new chat, and chat screens.

### Task 9: Final Regression And Sensitive Scan

**Files:**
- Inspect all modified files

**Step 1: Run full Python verification**

Run:

```powershell
$env:PYTHONNOUSERSITE='1'; conda run -n codex-accel python -m py_compile app.py mobile_portal.py custom_provider_proxy.py token_pool_proxy.py token_pool_settings.py process_singleton.py
$env:PYTHONNOUSERSITE='1'; conda run -n codex-accel python -m pytest tests
```

Expected: pass.

**Step 2: Run sensitive scan before any public commit or push**

Run:

```powershell
git grep -n "sk-\|github_pat_\|refresh_token\|access_token\|<private-provider-domain>\|<machine-local-service>" -- .
```

Expected: no real credentials or private provider defaults are introduced.

**Step 3: Review diff**

Run:

```powershell
git diff --stat
git diff -- app.py mobile_portal.py android-app/app/src/main/res tests
```

Expected: UI changes are scoped and existing private/local config remains outside committed artifacts.
