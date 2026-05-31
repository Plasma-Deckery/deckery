# Deckery

The Steam Deck is a genuinely capable handheld computer. Deckery's goal is to get the most productive and efficient work out of it — making full use of the unique combination of touch, trackpads, and controller buttons on the input side, while also shaping the OS to work well in this input mode and on the small screen.

Deckery is an umbrella for several subprojects:

---

### [deckery-hud](https://github.com/Plasma-Deckery/deckery-hud)
A live overlay showing what every button does right now. Controls should be discoverable and explain themselves — for easier onboarding and faster recall.

![Deckery HUD showing live button mappings on a Steam Deck diagram](https://raw.githubusercontent.com/Plasma-Deckery/deckery-hud/main/docs/hud-screenshot.png)

---

### [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery)
The input remapper. The goal is to be fully independent of Steam's input handler — reading raw evdev events directly, applying the config, emitting keyboard/mouse events without Steam in the loop.

Buttons, stick, and back paddles are fully covered. Trackpad scrolling is currently still handled by Steam Input — replacing it requires gesture recognition on the raw touch stream from HHD, which is an open problem. There's also room for improvement beyond what Steam offers: Steam Input only supports vertical scroll (circular gestures). A smarter recogniser could distinguish circles from straight strokes and use horizontal swipes for horizontal scroll. Contributions welcome.

![makima-deckery](docs/screenshots/makima-placeholder.png)

---

### [steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles)
System configuration and KDE patches managed with chezmoi.

![steamdeck-dotfiles](docs/screenshots/dotfiles-placeholder.png)

---

### [Kyanite](https://github.com/Plasma-Deckery/kyanite)
KWin script for dynamic workspace management — patched for single-column vertical grid layout.

---

### [maximized-window-gaps](https://github.com/Plasma-Deckery/maximized-window-gaps)
KWin script for configurable gaps around windows — patched for correct behaviour on the Steam Deck screen geometry.

---

## What it does

### Remapping

| Feature | Tool | Status |
|---|---|---|
| Steam-independent button remapping | [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) | ✅ Working |
| D-Pad, back paddles, all buttons | makima-deckery | ✅ Working |
| Right stick → cursor | makima-deckery | ✅ Working |
| Per-app button layouts | makima-deckery + kdotool | 📋 Planned |
| Config inheritance (`EXTENDS =`) | makima-deckery | 📋 Planned |

### HUD

See [deckery-hud](https://github.com/Plasma-Deckery/deckery-hud) for the full feature list and status.

### Radial menus

| Feature | Tool | Status |
|---|---|---|
| Context-aware radial menus | [Kando](https://github.com/kando-menu/kando) | 📋 Planned |

---

## Architecture

```
Steam Deck hardware
    │
    ├─ HHD (virtual Xbox device) ──────────────► Kando (radial menus)
    │
    └─ /dev/input/event* (evdev)
           │
           └─ makima-deckery ──────────────────► virtual keyboard/mouse device
                   │                                    │
                   ├─ /tmp/makima-state.json             └─► KDE / apps
                   └─ /tmp/makima.sock (IPC)
                           │
                           └─ deckery-hud
```

**makima-deckery** reads raw controller events, applies the config, emits keyboard/mouse events, and writes a fully-resolved state snapshot for the HUD. No Steam Input in the loop.

---

## Setup

### Steam Input

Deckery takes over buttons, stick navigation, and back paddles. Trackpad scrolling and mouse emulation still run through Steam Input for now — see the makima-deckery section above for the full picture.

To avoid conflicts with Steam Input on the parts Deckery does own:

1. **Lock the desktop controller config** so Steam can't overwrite it on restart:
   ```bash
   sudo chattr +i ~/.local/share/Steam/controller_base/desktop_neptune.vdf
   ```

2. **Disable Steam's right joystick handling** — in Steam's desktop controller settings, set group 25 (`right_joystick`) to `inactive`. This hands cursor control to makima-deckery's `RSTICK = "cursor"` mode.

### KDE patches

Two KWin scripts are patched and installed automatically via chezmoi. See [steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles) for the install scripts:

- **[maximized-window-gaps](https://github.com/Plasma-Deckery/maximized-window-gaps)** — configurable gaps around tiled windows; patched to avoid spurious unmaximize on resize
- **[Kyanite](https://github.com/Plasma-Deckery/kyanite)** — dynamic workspace management; patched for single-column vertical grid layout

---

## Upstream contributions

| Project | PR | Description |
|---|---|---|
| cyber-sushi/makima | [#57](https://github.com/cyber-sushi/makima/pull/57) | Fix BTN_DPAD_* silently ignored in config |
| cyber-sushi/makima | [#58](https://github.com/cyber-sushi/makima/pull/58) | Fix x11rb::connect panic after suspend |
| emberian/evdev | [#178](https://github.com/emberian/evdev/pull/178) | Add BTN_GRIPL/R/L2/R2 keycodes for Steam Deck back paddles |
| MurderFromMars/Kyanite | [#3](https://github.com/MurderFromMars/Kyanite/pull/3) | Vertical grid layout for single-column workspace switching |

---

## Device

Tested on: Steam Deck (Bazzite, KDE Plasma 6, Wayland)
Should work on: any handheld Linux device running HHD
