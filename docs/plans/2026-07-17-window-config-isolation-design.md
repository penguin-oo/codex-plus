# Window Configuration Isolation Design

## Goal

Bind each desktop Codex terminal to the backend configuration selected when that
terminal is opened. Later preset or backend changes affect only terminals opened
after the change. Model and reasoning effort remain adjustable inside a running
terminal.

## Constraints

- OAuth refresh tokens in `auth.json` cannot be safely copied between temporary
  `CODEX_HOME` directories.
- Session rollouts, SQLite state, goals, skills, plugins, and memories must remain
  available to every terminal.
- API keys, tokens, installation IDs, and private provider details remain local
  and must never enter the repository.
- The shared protocol translation proxy remains exclusive. This design does not
  attempt to run multiple incompatible proxy configurations concurrently.
- Preparing a terminal should add less than 100 ms on the normal local path.

## Architecture

Each launch captures one immutable in-memory copy of the current backend
settings. Argument generation, provider environment setup, proxy selection, and
runtime preparation all use this copy instead of reloading the settings file.

Every launch gets a small runtime record under
`%USERPROFILE%\.codex\window_profiles\<launch-id>`. The record holds lifecycle
metadata and, for an existing session, a write lock. It never stores an API key.

Codex Auth launches keep the normal `CODEX_HOME` so the live OAuth token remains
authoritative. Codex loads the selected provider and other startup configuration
once, and the launch-specific `-c` arguments remain fixed for that process.

Built-in token pool and OpenAI-compatible launches use a private temporary
`CODEX_HOME`. Its `config.toml`, model cache, and installation ID are launch
snapshots. Shared Codex directories are exposed through directory junctions.
`CODEX_SQLITE_HOME` points to the normal Codex home so goals and SQLite state are
not duplicated. Custom providers use environment-backed API keys and do not copy
`auth.json`.

## Launch Flow

1. Load backend settings once and copy the mapping.
2. Ensure the required shared proxy is ready.
3. Build model and provider overrides from the copied settings.
4. Create a runtime record and reject a second writable launch of the same
   session.
5. For non-auth modes, create the private Codex home and its shared directory
   junctions.
6. Build a PowerShell command that sets `CODEX_HOME`, `CODEX_SQLITE_HOME`, API
   environment variables, and the shell PID before starting Codex.
7. Run Codex in the terminal.
8. Remove the runtime record in a `finally` block. Periodic stale cleanup handles
   forced terminal closure or crashes.

## Cleanup Safety

Cleanup accepts only direct children of the configured runtime root and verifies
the launch marker before deleting anything. Reparse points are removed before
recursive deletion so shared target directories are never traversed. Pending
launches receive a grace period; runtime directories with a live shell PID are
preserved.

## Verification

- Unit tests cover private-home preparation, baseline installation ID selection,
  shared directory preservation, duplicate-session rejection, stale cleanup,
  and PowerShell environment binding.
- App tests prove one settings snapshot is used throughout command construction.
- A local loopback provider verifies that a private-home installation ID reaches
  Codex request metadata without contacting an external API.
- The full Python test suite and syntax compilation run before integration.
- A sensitive-data scan runs on the exact files changed by this feature.
