# Deckery

**Steam-independent, context-aware input stack for the Steam Deck (and other handheld Linux devices) in desktop mode.**

No Steam required for desktop input. Full controller support via makima — radial menus, per-app layouts, live HUD overlay.

---

## HUD

![Deckery HUD showing live button mappings on a Steam Deck diagram](docs/hud-screenshot.png)

The HUD overlays a transparent Steam Deck diagram with live button labels. It updates instantly when a modifier is held, when the focused app changes, or when the layout switches. No focus, no interaction — just information.

---

## What it does

| Feature | Tool | Status |
|---|---|---|
| Steam-independent button remapping | [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) | ✅ Working |
| D-Pad, back paddles, all buttons | makima-deckery | ✅ Working |
| Right stick → cursor | makima-deckery | ✅ Working |
| Live state export (`/tmp/makima-state.json`) | makima-deckery | ✅ Working |
| Pause/resume IPC (`/tmp/makima.sock`) | makima-deckery | ✅ Working |
| HUD overlay (eww, Steam Deck diagram) | deckery-hud | 🔧 In Progress |
| Radial menus per app context | [Kando](https://github.com/kando-menu/kando) | ✅ Working |
| Per-app button layouts | makima-deckery + kdotool | 📋 Planned |
| Config inheritance (`EXTENDS =`) | makima-deckery | 📋 Planned |

---

## Architecture

```
Steam Deck hardware
    │
    ├─ HHD (virtual Xbox device) ──────────────► Kando (radial menus, reads directly)
    │
    └─ /dev/input/event* (evdev)
           │
           └─ makima-deckery ──────────────────► virtual keyboard/mouse device
                   │                                    │
                   ├─ /tmp/makima-state.json             └─► KDE / apps
                   └─ /tmp/makima.sock (IPC)
                           │
                           └─ deckery-hud (eww overlay)
```

**makima-deckery** reads raw controller events, applies the config, emits keyboard/mouse events, and writes a fully-resolved state snapshot for the HUD. No Steam Input in the loop.

---

## Repos

| Repo | Description |
|---|---|
| [Plasma-Deckery/deckery](https://github.com/Plasma-Deckery/deckery) | This repo — configs, docs, patches |
| [Plasma-Deckery/makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) | Patched makima fork with state export + IPC |
| [Plasma-Deckery/deckery-hud](https://github.com/Plasma-Deckery/deckery-hud) | eww-based HUD overlay |
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
