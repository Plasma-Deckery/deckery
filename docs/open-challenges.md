# Open Challenges

Known hard problems and planned work. Each item links to the relevant GitHub issue.

## Lizard Mode suppression

The `hid-steam` kernel driver keeps a built-in mouse/scroll fallback (Lizard Mode) active unless suppressed via periodic hidraw HID reports. Steam handles this while running. Makima-deckery needs to take over this role for full Steam independence: open the hidraw device on startup, send feature reports `0x85` + `0x8d` every ~4s. The heartbeat is a useful safety mechanism — if makima crashes, Lizard Mode re-activates automatically.

→ [makima-deckery#11](https://github.com/Plasma-Deckery/makima-deckery/issues/11)

## Trackpad gesture tool

The virtual MT devices expose both trackpads to gesture tools (syngesture, fusuma, libinput-gestures). The missing piece is a minimal fork that outputs discrete gesture events to `/tmp/makima-control.sock` and sends haptic pulses via FF_HAPTIC. A tested, documented setup for this is still in progress.

→ [deckery#3](https://github.com/Plasma-Deckery/deckery/issues/3)

## Haptic feedback

Linux 6.18 introduced `FF_HAPTIC` for haptic-capable touchpads, and Bazzite ships kernel 6.19+. The infrastructure (hidraw fd held open for Lizard Mode suppression) doubles as the back-channel for sending haptic HID reports to the trackpad actuators.

→ [makima-deckery#9](https://github.com/Plasma-Deckery/makima-deckery/issues/9)

## On-screen keyboard

Finding a good keyboard alternative that works well in desktop mode without Steam. The Steam on-screen keyboard works well but requires Steam to be running. Voice input via OpenWhispr covers most free-text input at a desk; the remaining gap is structured input (passwords, PIN fields, forms) where dictation is impractical. A controller-native text entry UI for those cases would remove the last Steam dependency.

## libinput tuning for trackpad cursor

The virtual MT devices expose the trackpads to libinput, but libinput applies generic touchpad profiles to unknown devices. For good cursor movement with proper acceleration curves and inertia, the Deckery trackpad devices need custom libinput configuration — either via `libinput quirks` (device property overrides) or a minimal libinput fork. This is a prerequisite for making right-trackpad mouse movement feel as good as Steam Input's trackball mode.

→ [deckery#2](https://github.com/Plasma-Deckery/deckery/issues/2)

## Controller-native authentication input

Two places require a password or PIN without a keyboard: the lock screen, and system authentication prompts (sudo, polkit). The lock screen needs a controller-native PIN entry UI (d-pad or face buttons to select digits, confirm with A). For sudo/polkit, the existing system prompt dialogs would need to be intercepted or replaced with a controller-friendly equivalent — so that privilege escalation flows work without reaching for a keyboard.

→ [deckery#6](https://github.com/Plasma-Deckery/deckery/issues/6)
