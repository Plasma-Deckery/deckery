# Deckery

The Steam Deck is a genuinely capable handheld computer. Deckery's goal is to get the most productive and efficient work out of it — making full use of the unique combination of touch, trackpads, and controller buttons on the input side, while also shaping the OS to work well in this input mode and on the small screen.

Deckery is an umbrella for several subprojects:

---

### [deckery-hud](https://github.com/Plasma-Deckery/deckery-hud)
A live overlay showing what every button does right now. Controls should be discoverable and explain themselves — for easier onboarding and faster recall.

<video src="https://github.com/user-attachments/assets/728cf2dc-443e-446e-8714-4931174684ad" controls autoplay loop muted></video>

---

### [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery)
The input remapper. Two goals:

1. **Steam independence** — read raw evdev events directly, apply the config, emit keyboard/mouse events without Steam in the loop. We don't want to have to run Steam in the background in order to use the desktop mode efficiently.
2. **Richer control** — context-aware button layouts, per-app configs, and automations that go beyond what Steam Input allows.

**Progress**

| Area | Status |
|---|---|
| Buttons, D-Pad, back paddles, modifiers | ✅ Covered |
| Per-app button layouts | ✅ Covered |
| Trackpad scrolling | ⚠️ Currently via Steam Input — implementation planned |
| Trackpad cursor movement | ⚠️ Currently via Steam Input — libinput tuning required, planned |
| Full trackpad emulation (MT devices) | ✅ Available — `LPAD/RPAD = "trackpad"` |
| Trackpad gesture tools | 🔧 MT device ready; gesture tool integration planned ([deckery#3](https://github.com/Plasma-Deckery/deckery/issues/3)) |
| Lizard Mode suppression | 🔧 Required for full Steam independence — planned ([makima-deckery#11](https://github.com/Plasma-Deckery/makima-deckery/issues/11)) |
| Haptic feedback on trackpads | 🔧 Kernel support available in Linux 6.18+ / Bazzite 6.19+ — planned ([makima-deckery#9](https://github.com/Plasma-Deckery/makima-deckery/issues/9)) |
| On-screen keyboard | ⚠️ Better experience via Steam |

**Open challenges**

- **Lizard Mode suppression** — the `hid-steam` kernel driver keeps a built-in mouse/scroll fallback (Lizard Mode) active unless suppressed via periodic hidraw HID reports. Steam handles this while running. Makima-deckery needs to take over this role for full Steam independence: open the hidraw device on startup, send feature reports `0x85` + `0x8d` every ~4s. The heartbeat is a useful safety mechanism — if makima crashes, Lizard Mode re-activates automatically. See [makima-deckery#11](https://github.com/Plasma-Deckery/makima-deckery/issues/11).

- **Trackpad gesture tool** — the virtual MT devices expose both trackpads to gesture tools (syngesture, fusuma, libinput-gestures). The missing piece is a minimal fork that outputs discrete gesture events to `/tmp/makima-control.sock` and sends haptic pulses via FF_HAPTIC. A tested, documented setup for this is still in progress. See [deckery#3](https://github.com/Plasma-Deckery/deckery/issues/3).

- **Haptic feedback** — Linux 6.18 introduced `FF_HAPTIC` for haptic-capable touchpads, and Bazzite ships kernel 6.19+. The infrastructure (hidraw fd held open for Lizard Mode suppression) doubles as the back-channel for sending haptic HID reports to the trackpad actuators. See [makima-deckery#9](https://github.com/Plasma-Deckery/makima-deckery/issues/9).

- **On-screen keyboard** — finding a good keyboard alternative that works well in desktop mode without Steam. The Steam on-screen keyboard works well but requires Steam to be running. Voice input via OpenWhispr covers most free-text input at a desk; the remaining gap is structured input (passwords, PIN fields, forms) where dictation is impractical. A controller-native text entry UI for those cases would remove the last Steam dependency.

- **libinput tuning for trackpad cursor** — the virtual MT devices expose the trackpads to libinput, but libinput applies generic touchpad profiles to unknown devices. For good cursor movement with proper acceleration curves and inertia, the Deckery trackpad devices need custom libinput configuration — either via `libinput quirks` (device property overrides) or a minimal libinput fork. This is a prerequisite for making right-trackpad mouse movement feel as good as Steam Input's trackball mode. See [deckery#2](https://github.com/Plasma-Deckery/deckery/issues/2) for right-stick ball roll as an interim solution.

**Further challenges (out of scope, but relevant for handheld desktop use)**

- **PIN / lock screen entry** — the Steam Deck lock screen requires keyboard input for the login PIN. A controller-native PIN entry UI (d-pad or face buttons to select digits, confirm with A — similar to Steam's number pad) would make the device usable without attaching a keyboard for unlock.

- **Second-factor authentication** — TOTP prompts and passkey confirmations require text input or a hardware key. A controller-native TOTP entry flow, or integration with a software authenticator that can be triggered from the HUD, would remove the need to reach for a keyboard or phone.

Contributions welcome.

![makima-deckery](docs/screenshots/makima-placeholder.png)

---

### [Kyanite](https://github.com/Plasma-Deckery/kyanite)
KWin script for dynamic workspace management — patched for single-column vertical grid layout.

---

### [maximized-window-gaps](https://github.com/Plasma-Deckery/maximized-window-gaps)
KWin script for configurable gaps around windows — patched for correct behaviour on the Steam Deck screen geometry.

---

### [OpenWhispr](https://github.com/OpenWhispr/openwhispr) — voice input
Privacy-first, hotkey-activated voice-to-text running fully local via Whisper / NVIDIA Parakeet. On a handheld device without a physical keyboard, voice input is the practical text entry method when away from a desk — for messages, searches, quick notes. Triggered from makima via `BTN_TL + R5 → Ctrl+PgDn`.

Works well in quiet environments. Outdoor use is still imperfect — background noise and wind require a noise suppressor (e.g. RNNoise) in the audio pipeline. Not a full keyboard replacement but covers most on-the-go input needs.

---

### [steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles)
This is my personal dotfiles folder that also sets up scripts, panels, and settings in KDE. In the future I will document that better.

![steamdeck-dotfiles](docs/screenshots/dotfiles-placeholder.png)

---

## Architecture

```
/dev/input/event* (evdev)
       │
       └─ makima-deckery ──────────────────► virtual keyboard/mouse device
               │                            │                    │
               │                            ├─► KDE / apps       │
               │                            │                    │
               │                            └─► virtual trackpad MT devices
               │                                 (Deckery Left/Right Trackpad)
               │                                        │
               │                                        └─► libinput / gesture tools
               │
               ├─ /tmp/makima-state.json
               └─ /tmp/makima-control.sock (IPC)
                       │
                       └─ deckery-hud
```

**makima-deckery** reads raw controller events, applies the config, emits keyboard/mouse events, and writes a fully-resolved state snapshot for the HUD. When `LPAD/RPAD = "trackpad"` is set, it additionally exposes the trackpads as standard uinput MT devices, making them available to libinput and gesture tools. No Steam Input in the loop.

---

## Setup

### Steam Input

Deckery takes over buttons, stick navigation, and back paddles. Trackpad scrolling and mouse emulation still run through Steam Input for now — see the makima-deckery section above for the full picture.

> **Lizard Mode:** The `hid-steam` kernel driver keeps a built-in mouse/scroll fallback active at all times. Steam suppresses it while running. Until makima-deckery implements its own Lizard Mode suppression (planned for Phase 2), Steam needs to be running in the background for the trackpad emulation to work cleanly — otherwise the kernel driver's fallback behaviour interferes.

To avoid conflicts with Steam Input on the parts Deckery does own:

1. **Lock the desktop controller config** so Steam can't overwrite it on restart:
   ```bash
   sudo chattr +i ~/.local/share/Steam/controller_base/desktop_neptune.vdf
   ```

2. **Disable most of Steam's controller handling** — almost everything except trackpads and the Steam button is turned off in the desktop config. The full config is checked in at [`dot_local/share/Steam/controller_base/executable_desktop_neptune.vdf`](https://github.com/Plasma-Deckery/steamdeck-dotfiles/blob/main/dot_local/share/Steam/controller_base/executable_desktop_neptune.vdf) in steamdeck-dotfiles.

### KDE patches

Two KWin scripts are maintained as Plasma-Deckery forks and installed via chezmoi. See [steamdeck-dotfiles](https://github.com/Plasma-Deckery/steamdeck-dotfiles) for the install scripts:

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
