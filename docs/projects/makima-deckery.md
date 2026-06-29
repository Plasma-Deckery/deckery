# makima-deckery

**Repository:** [Plasma-Deckery/makima-deckery](https://github.com/Plasma-Deckery/makima-deckery)
**Fork of:** [cyber-sushi/makima](https://github.com/cyber-sushi/makima)

The input remapper at the core of Deckery. Reads raw evdev events directly from the kernel, applies a TOML config, and emits keyboard/mouse events via uinput — no Steam required.

## What it does

- **Steam independence** — reads `/dev/input/event*` directly, no Steam Input in the loop
- **Context-aware layouts** — per-app configs loaded automatically based on the focused window
- **Modifier keys** — hold a button to activate a second layer of bindings
- **Trackpad MT devices** — when `LPAD/RPAD = "trackpad"` is set, exposes the trackpads as standard uinput MT devices (`Deckery Left Trackpad`, `Deckery Right Trackpad`, combined `Deckery Trackpad`) for libinput and gesture tools
- **HUD state export** — on every input event, writes a fully-resolved state snapshot to `/tmp/makima-state.json` for deckery-hud to consume

## IPC

makima listens on a Unix socket at `/tmp/makima-control.sock`. Commands (newline-terminated):

| Command | Effect |
|---|---|
| `pause` | Suspend all remapping (Lizard Mode re-activates as fallback) |
| `resume` | Resume remapping |
| `analog-state-export on` | Write analog axis values into state JSON (used by HUD while open) |
| `analog-state-export off` | Stop writing analog values (default) |

## Config

Configs live in `~/.config/makima/`. The base config `Steam Deck.toml` is a symlink to `~/.local/share/deckery/deckery/configs/Steam Deck.toml` and is version-controlled. App-specific configs follow the naming pattern `Steam Deck::<AppName>.toml`.

Key config attributes:

| Attribute | Meaning |
|---|---|
| `no_pause = true` | Binding fires even when makima is paused |
| `no_off = true` | Binding fires even in Off mode (implies `no_pause`) |

## Changes from upstream

- Added `BTN_DPAD_*` support (merged upstream via [#57](https://github.com/cyber-sushi/makima/pull/57))
- Fixed x11rb panic after suspend (merged upstream via [#58](https://github.com/cyber-sushi/makima/pull/58))
- HUD state export (`/tmp/makima-state.json`)
- Lizard Mode suppression via hidraw heartbeat
- Virtual MT trackpad device exposure
- `no_pause` / `no_off` binding attributes
- IPC control socket

## Related

- [deckery-hud](deckery-hud.md) — consumes the state JSON
- [Open Challenges](../open-challenges.md) — Lizard Mode suppression, haptic feedback, trackpad cursor
