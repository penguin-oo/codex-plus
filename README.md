# Codex+

Codex+ is a Windows desktop and phone-control toolkit for local Codex CLI sessions. It gives you a desktop session browser, a mobile web portal, and an optional Android client for continuing Codex conversations from a phone.

The project is designed for local-first use. It does not ship API keys, account tokens, OpenAI auth files, proxy lists, or machine-specific settings. Every user must configure their own Codex account, token pool, or OpenAI-compatible API provider after cloning or downloading a release.

## Features

- Browse local Codex sessions from a Windows desktop UI.
- Resume existing sessions or start new sessions in selected folders.
- Use a phone browser or Android client through the mobile portal.
- Stop active replies and monitor reply status from the phone.
- Store per-session notes and per-account notes locally.
- Use one of three backend modes:
  - normal Codex auth from your local Codex CLI setup
  - built-in token-pool proxy for local token JSON files
  - OpenAI-compatible API presets for third-party compatible providers
- Expose the mobile portal through LAN, Tailscale, or your own public domain.
- Optionally restart another computer over SSH when you provide the host/user/key/password at runtime.

## What Is Not Included

This repository intentionally does not include:

- packaged zip/exe/apk files in git
- user API keys or provider presets
- Codex `auth.json` or account tokens
- token-pool files
- local IP addresses or private hostnames
- SSH private keys, SSH public keys, or passwords
- personal mobile portal tokens

Build artifacts should be distributed through GitHub Releases or your own build pipeline, not committed into the repository.

## Requirements

Desktop and portal:

- Windows 10/11
- Python 3.11+
- Codex CLI available in `PATH`
- Tkinter, usually included with the standard Python installer

Android client development:

- Android Studio or a compatible Gradle/JDK setup

Optional:

- Tailscale for private cross-network phone access
- Cloudflare Tunnel, Nginx Proxy Manager, Caddy, or another reverse proxy for domain access
- PuTTY `plink.exe` if you want password-based SSH restart from Windows

## New User Setup Checklist

Download or prepare:

- This project, either by cloning the repository or downloading a release source package.
- Python 3.11 or newer for the desktop manager and mobile portal.
- Codex CLI, installed and available as `codex` or `codex.cmd` in `PATH`.
- Windows Terminal is recommended for the desktop terminal experience.
- Android APK only if you want the native phone client; otherwise a phone browser is enough.
- Tailscale, Cloudflare Tunnel, Caddy, Nginx, or another proxy only if you need cross-network or domain access.

First-time configuration:

1. Verify Codex CLI works in a normal terminal:

```powershell
codex --version
codex login
```

2. Start the desktop manager:

```bat
run.bat
```

3. Start the mobile portal:

```bat
run-mobile.bat
```

4. Open the printed phone URL. Keep the `token` value private.
5. Choose one backend mode:
   - `Codex Auth` if your local Codex CLI login should be used.
   - `Built-In Token Pool` if you have local token JSON files.
   - `OpenAI-Compatible API` if you have a provider base URL and API credential.
6. If you use OpenAI-compatible API mode, create your own local preset in the app. Presets are stored locally in:

```text
%USERPROFILE%\.codex\token_pool_settings.json
```

7. If you use token-pool mode, place token files locally and do not commit them:

```text
%USERPROFILE%\.cli-proxy-api
```

8. If you use a domain, proxy HTTPS traffic to the portal:

```text
http://127.0.0.1:8765
```

9. If you use multiple computers, repeat the local configuration on each computer or copy only your own private config files manually. Do not publish those files to GitHub.

Local-only files you normally configure yourself:

- `%USERPROFILE%\.codex\config.toml`
- `%USERPROFILE%\.codex\token_pool_settings.json`
- `%USERPROFILE%\.codex\mobile_portal_settings.json`
- `%USERPROFILE%\.codex\installation_id`
- `%USERPROFILE%\.cli-proxy-api\...`
- any SSH keys, proxy lists, API keys, account tokens, or provider credentials

## Quick Start From Source

```powershell
git clone https://github.com/penguin-oo/codex-plus.git
cd codex-plus
```

Start the desktop manager:

```bat
run.bat
```

Start the mobile portal:

```bat
run-mobile.bat
```

The portal prints one or more URLs. Open one of them on your phone and include the printed `token` query parameter.

## Phone Access Options

### Same LAN

Start `run-mobile.bat` and use the LAN URL printed by the portal, for example:

```text
http://192.0.2.10:8765/?token=...
```

### Tailscale

Use this when the phone and PC are not on the same Wi-Fi but can join the same tailnet.

1. Install and sign in to Tailscale on the PC and phone.
2. Start `run-mobile.bat` on the PC.
3. Use the printed Tailscale URL, for example:

```text
http://desktop-name.tailnet-name.ts.net:8765/?token=...
```

### Domain Hosting

Use this when you want a normal domain such as `https://codex.example.com` to open the phone portal.

The portal listens locally on port `8765`. Your domain or tunnel must forward HTTPS traffic to:

```text
http://127.0.0.1:8765
```

Important security rules:

- Keep the `?token=...` value private.
- Use HTTPS for public domains.
- Do not expose the portal without the token.
- Prefer Tailscale for personal use; use public domains only when you understand the risk.

#### Cloudflare Tunnel Example

1. Install `cloudflared` on the Windows PC.
2. Authenticate Cloudflare:

```powershell
cloudflared tunnel login
```

3. Create a tunnel:

```powershell
cloudflared tunnel create codex-session-manager
```

4. Route your domain to the tunnel:

```powershell
cloudflared tunnel route dns codex-session-manager codex.example.com
```

5. Create `%USERPROFILE%\.cloudflared\config.yml`:

```yaml
tunnel: codex-session-manager
credentials-file: C:\Users\YOUR_USER\.cloudflared\TUNNEL_ID.json

ingress:
  - hostname: codex.example.com
    service: http://127.0.0.1:8765
  - service: http_status:404
```

6. Run the tunnel:

```powershell
cloudflared tunnel run codex-session-manager
```

7. Add the public base URL to `%USERPROFILE%\.codex\mobile_portal_settings.json`:

```json
{
  "public_urls": [
    "https://codex.example.com"
  ]
}
```

8. Restart `run-mobile.bat`. The portal will print a public URL with the current token.

#### Nginx/Caddy/Other Reverse Proxy

Forward your HTTPS domain to the Windows PC on port `8765`.

Example upstream:

```text
http://PC_LAN_IP:8765
```

Then add the domain to `%USERPROFILE%\.codex\mobile_portal_settings.json`:

```json
{
  "public_urls": [
    "https://codex.example.com"
  ]
}
```

Restart `run-mobile.bat` after editing the file.

## Backend Modes

Open the desktop manager and use the backend controls to choose one mode.

### Codex Auth

Uses your normal local Codex CLI authentication. This is the cleanest mode if `codex` already works in a terminal.

### Built-In Token Pool

Stores token JSON files under:

```text
%USERPROFILE%\.cli-proxy-api
```

The app starts a local proxy and rotates usable token files. Token files are local-only and should never be committed.

### OpenAI-Compatible API

Use this for providers that expose OpenAI-compatible or Codex-compatible endpoints.

General steps:

1. Open backend settings.
2. Choose OpenAI-Compatible API.
3. Add a preset name.
4. Enter the provider base URL.
5. Enter your own provider credential for that preset.
6. Save or refresh models.
7. Apply the preset.
8. Restart the local proxy if it is already running.

Provider notes:

- Some Codex-oriented providers require the Responses API and Codex CLI-style request headers.
- Some providers require a base URL with `/v1`; others require a custom path such as `/codex`.
- The app stores presets locally in `%USERPROFILE%\.codex\token_pool_settings.json`.
- Presets are not bundled with this repository.

## Startup Single-Instance Cleanup

When the desktop manager or mobile portal starts, it cleans older processes from this same project directory. This prevents duplicate `app.py`, `mobile_portal.py`, and local proxy instances from fighting over ports such as `8317` and `8765`.

The cleanup is scoped to this project path and does not kill unrelated Python processes.

Set this environment variable to disable startup cleanup:

```powershell
$env:CODEX_SESSION_MANAGER_SKIP_STARTUP_CLEANUP='1'
```

## Remote Restart Feature

The remote restart feature sends an SSH command to a host that you provide at runtime:

```text
shutdown /r /t 0
```

The repository does not hard-code a local IP, hostname, username, private key, or password. If you configure defaults, they are stored in your local `%USERPROFILE%\.codex\mobile_portal_settings.json` and should not be committed.

Password mode requires `plink.exe`. Key mode uses the system `ssh` client.

## Controlled Browser Attach

The browser attach tools assume you run a browser with a known remote-debugging port. Typical examples:

```text
http://127.0.0.1:9222
http://127.0.0.1:9223
```

Launcher scripts and profile paths are machine-specific. Keep them outside the repository or adapt them for your own environment.

## Build Releases

Build artifacts are intentionally ignored by git. Use GitHub Actions or local build commands to create release packages.

The workflow in `.github/workflows/release.yml` builds zip artifacts when you run it manually or push a version tag:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

GitHub Releases are the recommended place to publish downloads.

## Development

Run Python tests:

```powershell
python -m pytest
```

Compile-check key modules:

```powershell
python -m py_compile app.py mobile_portal.py custom_provider_proxy.py token_pool_proxy.py token_pool_settings.py process_singleton.py
```

## Privacy Checklist Before Publishing Forks

Before making your own fork public, verify:

- no files under `release/` are committed unless intentionally published
- no `.codex` files are committed
- no `.cli-proxy-api` token files are committed
- no API keys, access tokens, refresh tokens, SSH keys, or passwords are committed
- no personal hostnames or private IPs are committed
- no local `mobile_portal_settings.json` or `token_pool_settings.json` is committed
