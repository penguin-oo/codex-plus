# Codex+

Language: [中文](README.md) | English

Codex+ is a Windows desktop and mobile companion for managing Codex CLI sessions. It lets you browse, launch, resume, and clean up local Codex sessions on your PC, while also exposing a mobile portal that can be used from a phone browser or the Android app.

It is designed for these workflows:

- Managing many Codex sessions on a Windows machine.
- Checking Codex progress from a phone.
- Sending messages, uploading images, stopping replies, or starting new sessions from mobile.
- Switching between multiple Codex account slots.
- Switching backend modes between Codex Auth, Built-In Token Pool, and OpenAI-Compatible API providers.

## Screenshots

Screenshots are stored as repository files:

| Screen | File |
| --- | --- |
| Mobile home | [assets/mobile-home.jpg](assets/mobile-home.jpg) |
| Desktop overview | [assets/ui-overview.png](assets/ui-overview.png) |
| Accounts and backend settings | [assets/account-backend-redacted.png](assets/account-backend-redacted.png) |

## Features

- Desktop session list with time, model, working directory, last message, and details.
- Session actions: refresh, open terminal, open folder, open file, and delete.
- Launch options for model, approval mode, sandbox mode, search, and admin mode.
- Account slots: bind current account, switch account, rename, add notes, and delete.
- Backend modes:
  - `Codex Auth`: use the local Codex CLI login state.
  - `Built-In Token Pool`: proxy requests through a local token pool.
  - `OpenAI-Compatible API`: configure Base URL, API Key, model, protocol, and proxy mode.
- OpenAI-Compatible presets: save, refresh models, apply, and delete presets.
- Image input support for mobile and compatible API modes.
- Mobile portal with recent chats, all chats, new chat, chat details, and stop reply.
- Android app with a bundled debug APK and full source project.
- Optional SSH/Tailscale helper for restarting a configured PC.

## Requirements

Desktop app and mobile portal:

- Windows 10/11
- Python 3.11 or newer
- Codex CLI available as `codex` in `PATH`
- Python `requests[socks]`
- Tkinter, usually included with the official Windows Python installer

Android app build:

- JDK 17
- Android SDK
- Android SDK Platform 36
- Android Gradle Plugin 8.13.2
- Gradle 9.0.0 or a compatible newer version

Android app runtime:

- Android 8.0 or newer
- Phone access to the PC portal address, for example over LAN or Tailscale

## Install Dependencies

```powershell
py -3 -m pip install -r requirements.txt
```

For building the Windows EXE, install the build dependencies:

```powershell
py -3 -m pip install -r requirements-build.txt
```

Check that Codex CLI is available:

```powershell
codex --version
codex login
```

## Start the Desktop App

```bat
run.bat
```

The desktop app manages sessions, account slots, backend modes, and OpenAI-Compatible API presets.

## Start the Mobile Portal

```bat
run-mobile.bat
```

The command prints a portal URL. Open it from a phone browser, or use the same portal URL in the Android app.

## Android App

A debug APK is kept in the repository:

```text
app/CodexPlus-debug.apk
```

Android source code:

```text
android-app/
```

Build the debug APK:

```powershell
cd android-app
$env:ANDROID_HOME='your Android SDK path'
$env:ANDROID_SDK_ROOT='your Android SDK path'
gradle :app:assembleDebug --console=plain
```

Build output:

```text
android-app\app\build\outputs\apk\debug\app-debug.apk
```

## OpenAI-Compatible API

OpenAI-Compatible API presets can be configured from the desktop account/backend settings window. Each preset supports:

- Preset name
- Base URL
- API Key
- Model
- Proxy mode: `direct`, `proxy`, or `auto`
- Protocol: `responses` or `chat_completions`
- Disable image generation

After applying a preset, newly launched Codex sessions use that backend configuration.

## Project Layout

```text
.
├─ app.py                         # Windows desktop manager
├─ mobile_portal.py               # Mobile portal service
├─ token_pool_proxy.py            # Built-In Token Pool local proxy
├─ custom_provider_proxy.py       # OpenAI-Compatible protocol adapter
├─ token_pool_settings.py         # Backend mode and preset storage
├─ auth_slots.py                  # Codex account slot management
├─ controlled_browser.py          # Controlled browser helpers
├─ process_singleton.py           # Old process cleanup for this project
├─ remote_ssh.py                  # Remote restart SSH helper
├─ session_context_repair.py      # Session context repair helper
├─ run.bat                        # Start desktop app
├─ run-mobile.bat                 # Start mobile portal
├─ requirements.txt               # Runtime dependencies
├─ requirements-build.txt         # Build dependencies
├─ app/
│  └─ CodexPlus-debug.apk         # Android debug APK
├─ android-app/                   # Android app source
├─ assets/                        # README screenshots
└─ scripts/
   └─ ensure-boot-network.ps1     # Boot-time network helper
```

## Build Windows EXE

The project includes a PyInstaller spec:

```powershell
pyinstaller codex-session-manager.spec
```

Output directory:

```text
dist\
```

## Distribution

This project currently does not use GitHub Releases. The installable Android APK is kept in the repository:

```text
app/CodexPlus-debug.apk
```
