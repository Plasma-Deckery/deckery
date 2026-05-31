# Deckery

The Steam Deck is a genuinely capable handheld computer. Deckery's goal is to get the most productive and efficient work out of it — making full use of the unique combination of touch, trackpads, and controller buttons on the input side, while also shaping the OS to work well in this input mode and on the small screen.

Deckery is an umbrella for several subprojects:

---

### [deckery-hud](https://github.com/Plasma-Deckery/deckery-hud)
A live overlay showing what every button does right now — controls should explain themselves.

![Deckery HUD showing live button mappings on a Steam Deck diagram](https://raw.githubusercontent.com/Plasma-Deckery/deckery-hud/main/docs/hud-screenshot.png)

---

### [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery)
The input remapper. Reads raw evdev events directly, applies the config, emits keyboard/mouse events — independent of Steam Input and the Steam process. This makes the full remapping stack available in any desktop session without Steam running in the background, and gives more control over every button, axis, and paddle than Steam Input allows.

![makima-deckery](docs/screenshots/makima-placeholder.png)

---

### [steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles)
System configuration and KDE patches managed with chezmoi.

![steamdeck-dotfiles](docs/screenshots/dotfiles-placeholder.png)

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

Deckery takes over buttons, stick navigation, and back paddles. Trackpad scrolling and mouse emulation still run through Steam Input for now — replacing those requires gesture recognition on raw HHD touch events, which is an open problem (see below).

To avoid conflicts with Steam Input on the parts Deckery does own:

1. **Lock the desktop controller config** so Steam can't overwrite it on restart:
   ```bash
   sudo chattr +i ~/.local/share/Steam/controller_base/desktop_neptune.vdf
   ```

2. **Disable Steam's right joystick handling** — in Steam's desktop controller settings, set group 25 (`right_joystick`) to `inactive`. This hands cursor control to makima-deckery's `RSTICK = "cursor"` mode.

#### Trackpad scrolling — open problem

The circular-gesture-to-scroll behaviour currently comes from Steam Input. Whether it can be replaced without Steam is an open question — it would need gesture recognition directly on the raw touch stream from HHD.

There's also room for improvement beyond what Steam offers: Steam Input only supports vertical scroll (clockwise/counterclockwise circles). A smarter recogniser could distinguish circles from straight strokes and use horizontal swipes for horizontal scroll — or pick the scroll axis from the direction of the initial movement. If you're interested in working on this, contributions are very welcome.

### KDE patches

Two KWin scripts are patched and installed automatically via chezmoi. See [steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles) for the install scripts:

- **[maximized-window-gaps](https://github.com/Plasma-Deckery/maximized-window-gaps)** — configurable gaps around tiled windows; patched to avoid spurious unmaximize on resize
- **[Kyanite](https://github.com/Plasma-Deckery/kyanite)** — dynamic workspace management; patched for single-column vertical grid layout

### HUD

The HUD (deckery-hud) runs inside a [distrobox](https://github.com/containers/distrobox) container (`deckery`) because `gtk4-layer-shell` is not available as a GObject Typelib on the host. See [deckery-hud](https://github.com/Plasma-Deckery/deckery-hud) for setup.

---

## Repos

| Repo | Description |
|---|---|
| [Plasma-Deckery/deckery](https://github.com/Plasma-Deckery/deckery) | This repo — configs, docs, patches |
| [Plasma-Deckery/makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) | Patched makima fork with state export + IPC |
| [Plasma-Deckery/deckery-hud](https://github.com/Plasma-Deckery/deckery-hud) | HUD overlay |
| [Plasma-Deckery/steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles) | System dotfiles |

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
