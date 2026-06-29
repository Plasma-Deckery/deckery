# Deckery

The Steam Deck is a genuinely capable handheld computer. Deckery's goal is to get the most productive and efficient workflows out of it — making full use of the unique combination of touch, trackpads, and controller buttons on the input side, while also shaping the OS to work well in this input mode and on the small screen.

The goal: fast and intuitive control of the device — without needing an external keyboard, and without relying on Steam running in the background.

## What's included

**[makima-deckery](https://github.com/Plasma-Deckery/makima-deckery)** — The input remapper. Reads raw controller events directly from the kernel, applies context-aware button configs, and emits keyboard/mouse events. No Steam required. Per-app layouts, modifier keys, trackpad gestures.

**[deckery-hud](https://github.com/Plasma-Deckery/deckery-hud)** — A live overlay showing what every button does right now. Controls explain themselves — no guessing, no memorising.

**deckery-tray** — System tray applet: service status at a glance, quick restart, pause/resume, and access to your config folder.

**[steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles)** — An opinionated KDE setup tuned for the Steam Deck's screen and input methods. Workspace management, panel layout, KWin scripts.

## Getting started

→ [Setup Guide](setup-guide.md)

## How it works

```
/dev/input/event* (evdev)
       │
       └─ makima-deckery ──────────────────► virtual keyboard/mouse device
               │                            │
               │                            └─► virtual trackpad MT devices
               │                                 (Deckery Left/Right Trackpad)
               │                                        │
               │                                        └─► libinput / gesture tools
               │
               ├─ /tmp/makima-state.json  ──► deckery-hud (live button map)
               └─ /tmp/makima-control.sock   (IPC: pause, resume, …)
```

makima-deckery writes a fully-resolved state snapshot on every input event. deckery-hud watches this file and renders the overlay — no logic duplication between the two.

When `LPAD/RPAD = "trackpad"` is set, makima additionally exposes the trackpads as standard uinput MT devices, making them available to libinput and gesture tools.

## Progress

| Area | Status |
|---|---|
| Buttons, D-Pad, back paddles, modifiers | ✅ Covered |
| Per-app button layouts | ✅ Covered |
| Trackpad scrolling | ⚠️ Better via Steam Input — planned ([deckery#4](https://github.com/Plasma-Deckery/deckery/issues/4)) |
| Trackpad cursor movement | ⚠️ Better via Steam Input — planned ([deckery#5](https://github.com/Plasma-Deckery/deckery/issues/5)) |
| Trackpad gestures | ✅ MT devices emulated — gesture tool integration planned ([deckery#3](https://github.com/Plasma-Deckery/deckery/issues/3)) |
| Lizard Mode suppression | 🔧 In progress ([makima-deckery#11](https://github.com/Plasma-Deckery/makima-deckery/issues/11)) |
| Haptic feedback | 🔧 Kernel support in 6.18+ — planned ([makima-deckery#9](https://github.com/Plasma-Deckery/makima-deckery/issues/9)) |
| On-screen keyboard | ⚠️ Better via Steam |

→ [Open Challenges](open-challenges.md) for details on the hard unsolved problems.
→ [Contributions](projects/index.md) for a full list of projects and upstream PRs.
