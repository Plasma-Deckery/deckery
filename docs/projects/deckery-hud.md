# deckery-hud

**Repository:** [Plasma-Deckery/deckery-hud](https://github.com/Plasma-Deckery/deckery-hud)

A live overlay that shows what every button does right now. Controls should explain themselves — for faster recall and easier onboarding.

## What it does

- **HUD overlay** — hold L1 to reveal the full button map. Displays the current context, active modifier, and every bound action. Hides when L1 is released.
- **OSD overlay** — always-visible transparent layer showing the current controller state (which buttons are held, analog positions). Disappears while the HUD is open.
- **Toast notifications** — brief on-screen messages for mode changes (e.g. "Remapping off").
- **Remapping toggle** — button in the HUD title bar to enable/disable makima remapping without leaving the overlay.

## Architecture

Built with GTK4 + gtk4-layer-shell (Wayland Layer Shell protocol). Two persistent windows:

| Window | Type | Input region |
|---|---|---|
| `Win` | HUD overlay | Small region for title bar buttons |
| `OsdWin` | OSD overlay | None — fully click-through |

Both windows are Wayland layer-shell surfaces anchored to the center of the screen. The OSD runs at all times; the HUD is shown/hidden on demand.

## D-Bus interface

deckery-hud registers as `de.plasma_deckery.hud` on the session bus. Methods:

| Method | Effect |
|---|---|
| `Toggle` | Show HUD if hidden, hide if visible |
| `Show` | Show the HUD |
| `Hide` | Hide the HUD |

Triggered by makima bindings, e.g.:
```toml
L1 = "dbus de.plasma_deckery.hud /de/plasma_deckery/hud de.plasma_deckery.hud Toggle"
```

## State file

Watches `/tmp/makima-state.json` via GLib FileMonitor. On change, updates the button map display without re-implementing any of makima's lookup logic.

## Related

- [makima-deckery](makima-deckery.md) — produces the state JSON and IPC socket
