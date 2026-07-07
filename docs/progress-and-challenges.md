# Progress & Challenges

## What works

| Area | Status |
|---|---|
| Buttons, D-Pad, back paddles, modifiers | ✅ Covered |
| Per-app button layouts | ✅ Covered |
| System tray (service status, control, updates) | ✅ Covered |
| One-line installation script | ✅ Covered |

## Future work

| Area | Status |
|---|---|
| Trackpad gestures | 🔧 MT device emulation in progress ([feat/trackpad-mt-translation](https://github.com/Plasma-Deckery/makima-deckery/tree/feat/trackpad-mt-translation)) — gesture tool integration planned ([deckery#3](https://github.com/Plasma-Deckery/deckery/issues/3)) |
| Pinch-zoom and two-pad gestures | 🔧 Both pads as a combined two-finger device — enables pinch-zoom, horizontal scroll, and two-axis pan ([deckery#7](https://github.com/Plasma-Deckery/deckery/issues/7)) |
| Trackpad scrolling | ⚠️ Better experience via Steam Input — implementation planned ([deckery#4](https://github.com/Plasma-Deckery/deckery/issues/4)) |
| Trackpad cursor movement | ⚠️ Better experience via Steam Input — implementation planned ([deckery#5](https://github.com/Plasma-Deckery/deckery/issues/5)) |
| Lizard Mode suppression | 🔧 In progress — hidraw heartbeat implemented, configurable via `SUPPRESS_LIZARD_MODE` ([makima-deckery#11](https://github.com/Plasma-Deckery/makima-deckery/issues/11)) |
| Haptic feedback on trackpads | 🔧 Kernel support available in Linux 6.18+ / Bazzite 6.19+ — planned ([makima-deckery#9](https://github.com/Plasma-Deckery/makima-deckery/issues/9)) |
| Trackpad hardware settings | 🔧 Expose trackpad sensitivity, pressure thresholds, and haptic intensity via makima config — planned ([makima-deckery#13](https://github.com/Plasma-Deckery/makima-deckery/issues/13)) |
| On-screen keyboard | ⚠️ Better experience via Steam |

## Open Challenges

Known hard problems and planned work. Each item links to the relevant GitHub issue.

The trackpad-related challenges below are coordinated in [Epic #16 — Steam-independent trackpad stack](https://github.com/Plasma-Deckery/deckery/issues/16).

### Lizard Mode suppression

The `hid-steam` kernel driver keeps a built-in mouse/scroll fallback (Lizard Mode) active unless suppressed via periodic hidraw HID reports. Steam handles this while running. Makima-deckery needs to take over this role for full Steam independence: open the hidraw device on startup, send feature reports `0x85` + `0x8d` every ~4s. The heartbeat is a useful safety mechanism — if makima crashes, Lizard Mode re-activates automatically. See [makima-deckery#11](https://github.com/Plasma-Deckery/makima-deckery/issues/11).

### Trackpad gesture tool

The virtual MT devices expose both trackpads to gesture tools (syngesture, fusuma, libinput-gestures). The missing piece is a minimal fork that outputs discrete gesture events to `/tmp/makima-control.sock` and sends haptic pulses via FF_HAPTIC. A tested, documented setup for this is still in progress. See [deckery#3](https://github.com/Plasma-Deckery/deckery/issues/3).

### Haptic feedback

Linux 6.18 introduced `FF_HAPTIC` for haptic-capable touchpads, and Bazzite ships kernel 6.19+. The infrastructure (hidraw fd held open for Lizard Mode suppression) doubles as the back-channel for sending haptic HID reports to the trackpad actuators. See [makima-deckery#9](https://github.com/Plasma-Deckery/makima-deckery/issues/9).

### On-screen keyboard

Finding a good keyboard alternative that works well in desktop mode without Steam. The Steam on-screen keyboard works well but requires Steam to be running. Voice input via OpenWhispr covers most free-text input at a desk; the remaining gap is structured input (passwords, PIN fields, forms) where dictation is impractical. A controller-native text entry UI for those cases would remove the last Steam dependency.

### libinput tuning for trackpad cursor

The virtual MT devices expose the trackpads to libinput, but libinput applies generic touchpad profiles to unknown devices. For good cursor movement with proper acceleration curves and inertia, the Deckery trackpad devices need custom libinput configuration — either via `libinput quirks` (device property overrides) or a minimal libinput fork. This is a prerequisite for making right-trackpad mouse movement feel as good as Steam Input's trackball mode. See [deckery#2](https://github.com/Plasma-Deckery/deckery/issues/2) for right-stick ball roll as an interim solution.

### Controller-native authentication input

Two places require a password or PIN without a keyboard: the lock screen, and system authentication prompts (sudo, polkit). The lock screen needs a controller-native PIN entry UI (d-pad or face buttons to select digits, confirm with A). For sudo/polkit, the existing system prompt dialogs would need to be intercepted or replaced with a controller-friendly equivalent — so that privilege escalation flows work without reaching for a keyboard. See [Epic #17](https://github.com/Plasma-Deckery/deckery/issues/17) for the full staged implementation plan.

---

Further challenges and planned work are tracked in the issues of the individual subprojects and in the [main Deckery issue tracker](https://github.com/Plasma-Deckery/deckery/issues).
