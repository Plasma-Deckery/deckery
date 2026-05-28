# Deckery

The Steam Deck shouldn't need Steam running to be useful in desktop mode. Deckery is an attempt to build a proper input stack directly on the hardware — independent of the Steam process, with more control and more room to experiment than Steam Input allows.

Deckery is an umbrella for several subprojects. The **HUD** is the central one: a live, interactive guide to your current shortcuts — so you never have to memorise layouts or dig through config files.

---

## HUD

![Deckery HUD showing live button mappings on a Steam Deck diagram](docs/hud-screenshot.png)

The HUD overlays a transparent Steam Deck diagram showing what every button does right now. Hold a modifier and the full combo layer appears instantly. The idea is simple: controls should explain themselves — whether you're learning a new layout, picking up the device after a long break, or handing it to someone else. Per-app layout switching is planned for a future release.

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

| Feature | Tool | Status |
|---|---|---|
| Steam Deck diagram overlay | deckery-hud | 🔧 In Progress |
| Live button labels | deckery-hud | 🔧 In Progress |
| Modifier overlay (live shortcut view) | deckery-hud | 🔧 In Progress |
| Per-app context switching | deckery-hud | 📋 Planned |

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
