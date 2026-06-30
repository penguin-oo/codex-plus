# UI Refresh Design

## Goal

Improve the desktop manager, mobile web portal, and Android client UI without changing their core behavior. The result should feel like one local-first operations tool: calm, dense enough for repeated use, readable on desktop and phone, and free of private machine/provider assumptions.

## Product Shape

This project is not a marketing site. It is a working surface for local Codex sessions, backend mode control, notes, MCP/skills inspection, and phone continuation. The UI should prioritize scanability, fast session selection, clear launch settings, and reliable chat composition.

## Visual Thesis

A restrained utility interface with neutral surfaces, crisp dividers, compact controls, and one teal-green accent reserved for primary actions and active states.

## Direction

Use the conservative unified visual system route. Keep the current Python, Tkinter/ttk, mobile portal, and Android XML architecture. Improve hierarchy and ergonomics in place instead of rewriting navigation or data flow.

## Desktop UI

The desktop app should remain a table-first manager. The top toolbar should group common actions and expose status without crowding the window. Launch options should read as a configuration bar, not as the main visual object. The session table should get clearer row height, column hierarchy, zebra striping, selection color, and header styling. The details area should feel like an inspector with calmer tabs and readable text.

Implementation should stay inside `app.py` and reuse ttk where possible. New behavior is not required in this phase.

## Mobile Web UI

The web portal should start with the working surface, not a large hero panel. It should keep sessions, MCP, skills, backend, and remote controls, but reduce nested cards, heavy shadows, radial backgrounds, and oversized rounded corners. On desktop-width browser views, the layout should keep a compact left workspace and a larger chat/detail area. On phone widths, sessions and details should stack cleanly, controls should remain tappable, and the composer should be easy to use.

Implementation should stay inside `mobile_portal.py` and preserve existing API calls and element IDs.

## Android UI

The Android app should keep AppCompat XML/ViewBinding. The theme should move from the current heavy deep-blue card stack to a cleaner dark neutral system shared with the web portal. Cards, panels, message bubbles, quick actions, and composer controls should use smaller radii, softer contrast, and consistent spacing. The chat screen should keep the current send/stop/image behaviors.

Implementation should primarily update XML resources, drawables, and minor layout spacing. Java behavior should only change if visual state requires it.

## Constraints

- Do not expose local keys, tokens, machine IDs, provider names, or special API settings.
- Do not hard-code local service names or provider branches into UI defaults.
- Do not remove existing controls or break current tests.
- Keep changes incremental and easy to verify.
- Preserve current modified worktree state; do not revert unrelated changes.

## Verification

Run Python compile and tests after Python/mobile web changes. Run Android debug build after Android resource/layout changes. Perform visual checks for desktop, desktop browser width, phone browser width, and Android build output where feasible.
