# Progress & Challenges

## What works

| Area | Status |
|---|---|
| Buttons, D-Pad, back paddles, modifiers | ✅ Covered |
| Per-app button layouts | ✅ Covered |
| Lizard Mode suppression | ✅ Covered — hidraw heartbeat keeps Steam Deck controller in full mode |
| Suspend/resume reconnect | ✅ Covered — in-process reinit, ~1s recovery window |
| Trackpad cursor movement | ✅ Works — right trackpad as mouse via virtual MT device and libinput. No inertial trackball yet (see challenges below). |
| Trackpad scrolling | ✅ Works — two-finger gesture via virtual MT device. Better than Steam Input. Single-trackpad scroll may be added in the future. |
| Trackpad gestures (pinch-zoom, pan, scroll) | ✅ Works — both pads exposed as a combined two-finger MT device |
| Haptic feedback on trackpads | ✅ Partially covered — makima sends haptic pulses on click press/release via hidraw; advanced tuning (gain, pulse shape) is an open issue ([makima-deckery#20](https://github.com/Plasma-Deckery/makima-deckery/issues/20)) |
| Trackpad hardware settings | ✅ Partially covered — config fields exist for click pressure and trackpad mode; click pressure threshold not yet sent to firmware ([makima-deckery#26](https://github.com/Plasma-Deckery/makima-deckery/issues/26)) |
| On-screen keyboard | ✅ Works — choose between the Steam keyboard (Steam+X) and the Plasma keyboard (enable in Settings) |
| Steam Input disable | ✅ Covered — via Steam's own configset mechanism; tray shows status and handles the transition |
| System tray (service status, control, updates) | ✅ Covered |
| One-line installation script | ✅ Covered |

## Future work

| Area | Status |
|---|---|
| Gesture tool integration | 🔧 Forward gesture events to syngesture/fusuma/libinput-gestures via control socket ([deckery#3](https://github.com/Plasma-Deckery/deckery/issues/3)) |
| Controller-native authentication | 🔧 Lock screen PIN entry, sudo/polkit prompts ([Epic #17](https://github.com/Plasma-Deckery/deckery/issues/17)) |
| Accessibility tree navigation | 🔧 D-Pad navigation in native OS menus via AT-SPI2 ([Epic #22](https://github.com/Plasma-Deckery/deckery/issues/22)) |

## Open Challenges

Known hard problems that don't have a clean solution yet.

### Inertial trackball for cursor movement

The right trackpad works as a mouse via libinput, but libinput applies generic touchpad profiles to unknown devices. For the trackball feel of Steam Input — with proper acceleration curves and momentum after lifting the finger — the Deckery trackpad devices need custom libinput configuration (libinput quirks or a device-specific profile). Without this, fast cursor throws don't coast.

### Controller-native authentication input

Two places require a password or PIN without a keyboard: the lock screen, and system authentication prompts (sudo, polkit). The lock screen needs a controller-native PIN entry UI; sudo/polkit prompts need a controller-friendly equivalent. See [Epic #17](https://github.com/Plasma-Deckery/deckery/issues/17).

---

Further challenges and planned work are tracked in the [main Deckery issue tracker](https://github.com/Plasma-Deckery/deckery/issues).
