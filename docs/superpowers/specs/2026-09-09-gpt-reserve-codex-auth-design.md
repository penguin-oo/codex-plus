# GPT Reserve Codex Auth Model Design

## Goal

Allow the desktop and mobile chat manager to select and pass the internal
`gpt-reserve` model to the official Codex CLI when the backend is
`Codex Auth`, without exposing that account-scoped model to token-pool or
OpenAI-compatible API backends.

## Scope

- Add `gpt-reserve` to the Codex Auth model choices in desktop and mobile UI.
- Preserve the existing CLI launch behavior so selected models are passed with
  `-m gpt-reserve` for new and resumed chats.
- Pass a Codex Auth-only static `model_catalog_json` override so interactive
  `/model` can keep the reserve entry visible after the CLI refreshes its cache.
- Keep API-key, token-pool, and custom-provider model lists unchanged.
- Do not synthesize quota, change authentication, or automatically retry a
  rejected reserve request.

## Design

The shared model constants will distinguish ordinary fallback models from the
Codex Auth-only reserve model. Desktop and mobile model catalog builders will
include the reserve model only when they are building the official-auth
catalog. Existing launch argument builders already pass the selected model to
the CLI, so no provider or proxy translation is added.

The manager generates the static catalog from the current Codex model cache and
changes only the reserve entry's picker visibility. It is passed per launch,
so the global `config.toml` is not changed. A local catalog entry cannot grant
Luna Reserve entitlement; the account and supported Codex client must still
expose the reserve allowance.

## Verification

- Desktop Codex Auth model choices include `gpt-reserve`.
- Mobile Codex Auth model choices include `gpt-reserve`.
- Desktop and mobile new/resume launch arguments contain `-m gpt-reserve`.
- Desktop and mobile Codex Auth launches pass the static model catalog override.
- Token-pool and OpenAI-compatible model catalogs do not gain `gpt-reserve`.
- Existing model selection and backend routing tests remain green.
