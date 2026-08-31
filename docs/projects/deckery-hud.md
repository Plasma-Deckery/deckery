# Deckery HUD

**Repository:** [Plasma-Deckery/deckery-hud](https://github.com/Plasma-Deckery/deckery-hud)

A live overlay for visualising and exploring your button config. See what every button does right now — controls should be discoverable and explain themselves, for easier onboarding and faster recall.

<video src="https://github.com/user-attachments/assets/728cf2dc-443e-446e-8714-4931174684ad" controls autoplay loop muted></video>

## What it does

### HUD overlay

Toggle open (default: L3) to pause remapping and inspect your full button layout:

- Renders two Steam Deck silhouettes (front + back) with callout lines to button labels
- Updates live from `/tmp/makima-state.json` — written atomically by makima-deckery on every input event
- Pauses makima remapping while open — dry-run mode: see what buttons do without triggering anything
- Center strip shows the active modifier state and the currently held output keys
- Trackpad and stick positions rendered as analog overlays on the silhouette
- Dot colours: **amber** = modifier held, **white** = button active, **gray** = unbound
- Small amber dot on buttons that would unlock a combo if held next (discoverable modifiers)
- Cyan underline diamond accent on modifier buttons that have app-specific combos — distinguishes app-tailored shortcuts from base-config combos at a glance

### OSD (On-Screen Display)

Always-on transparent overlay — active even when the HUD is closed:

- Shows currently held output keys as cyan pills at the bottom of the screen
- Fires a toast notification on every action (key combo, command, exec)
- Fully input-transparent — no clicks, no interference with anything underneath
- `silent = true` bindings (e.g. mouse clicks) are suppressed from the OSD but still visible in the HUD center strip

## Configuration

Two things can be configured by the user:

- **HUD toggle binding** — which button opens and closes the HUD. Set via a makima binding that calls `Toggle` on the D-Bus interface (see below). Default: L3.
- **OSD on/off** — the OSD can be enabled or disabled independently of the HUD, e.g. via the deckery-tray menu.

## Analog data and the HUD

Normally, makima does not write analog values (stick and trackpad positions) to the state JSON — doing so on every input event would produce too much data. When the HUD is opened, it sends an IPC command to makima to enable analog reporting. When the HUD is closed, it sends the command to disable it again. This way, the analog overlays on the silhouette are always current while the HUD is visible, without any overhead when it is not.

## Architecture

Built with GTK4 + gtk4-layer-shell (Wayland Layer Shell protocol). Two persistent windows:

| Window | Type | Input region |
|---|---|---|
| `Win` | HUD overlay | Recalculated on every draw to cover only the visible close/title bar buttons |
| `OsdWin` | OSD overlay | None — fully click-through |

Both windows are Wayland layer-shell surfaces anchored to the center of the screen. The OSD runs at all times; the HUD is shown/hidden on demand.

```
makima-deckery ──► /tmp/makima-state.json
                           │
                      deckery-hud
                    (GTK4, Layer Shell)
                  persistent D-Bus service
                           │
               ┌───────────┴───────────┐
             HUD window             OSD window
          (shown on toggle)      (always visible)
               └───────────┬───────────┘
                            │
                     renderer.py          makima IPC
                   (SVG + Cairo/Pango)   pause / resume
```

## D-Bus interface

deckery-hud registers as `de.plasma_deckery.hud` on the session bus. Methods:

| Method | Effect |
|---|---|
| `Toggle` | Show HUD if hidden, hide if visible |
| `Show` | Show the HUD |
| `Hide` | Hide the HUD |

Triggered by makima bindings, e.g.:

```toml
L3 = "dbus de.plasma_deckery.hud /de/plasma_deckery/hud de.plasma_deckery.hud Toggle"
```

## State file

Watches `/tmp/makima-state.json` via GLib FileMonitor. On change, updates the button map display without re-implementing any of makima's lookup logic. See [State JSON](../reference/state-json.md) for the full format.
