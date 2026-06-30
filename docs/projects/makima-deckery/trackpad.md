# Trackpad Emulation

The Steam Deck trackpads are capable input surfaces, but the raw events they produce are not visible to gesture tools — those expect standard Linux multi-touch devices. Makima-deckery translates the raw trackpad data into proper MT events and exposes virtual uinput devices, making both pads available to tools like `libinput-gestures` or `fusuma`.

## How it works

The Steam Deck kernel driver (`hid-steam`) delivers trackpad data as absolute axes on the gamepad device:

| Raw axis | Meaning | Range |
|---|---|---|
| `ABS_HAT0X` / `ABS_HAT0Y` | Left trackpad position | −32767 … +32767 |
| `ABS_HAT1X` / `ABS_HAT1Y` | Right trackpad position | −32767 … +32767 |
| `BTN_THUMB` | Left trackpad physical click | — |
| `BTN_THUMB2` | Right trackpad physical click | — |

Makima translates these to `ABS_MT_POSITION_X/Y` + `BTN_TOUCH` + `BTN_TOOL_FINGER` frames on the virtual uinput device. The Y-axis is corrected to libinput convention — hardware reports up as negative; the virtual device flips this.

Once the virtual devices exist, gesture tools read them and map swipes, taps, and zones to arbitrary actions — independently configurable per pad.

## Virtual devices

With `LPAD = "trackpad"` or `RPAD = "trackpad"` in the config, makima creates:

| Device name | Source |
|---|---|
| `Deckery Left Trackpad` | Left trackpad (`ABS_HAT0X/Y`) |
| `Deckery Right Trackpad` | Right trackpad (`ABS_HAT1X/Y`) |
| `Deckery Trackpad` | Both pads combined into a single MT device |

## Configuration

```toml
[settings]
LPAD = "trackpad"   # creates "Deckery Left Trackpad" virtual MT device
RPAD = "trackpad"   # creates "Deckery Right Trackpad" virtual MT device
# LPAD = "disabled" # default — no virtual device
```

Trackpad position, touch state, and press state are always tracked and exported to `state.json` regardless of the mode setting — the HUD can visualise trackpad input even when mode is `"disabled"`.

## Lizard Mode

Full Steam independence requires suppressing the `hid-steam` kernel driver's built-in mouse/scroll fallback (Lizard Mode). While Steam is running, Steam handles this automatically. Makima-native Lizard Mode suppression is in progress — see [makima-deckery#11](https://github.com/Plasma-Deckery/makima-deckery/issues/11).

## libinput tuning

When the virtual devices are registered, libinput applies generic touchpad profiles to them. For good cursor movement and gesture recognition, the Deckery trackpad devices may need custom libinput configuration via `libinput quirks`. This is a prerequisite for making the trackpad feel as responsive as Steam Input's trackball mode. See [deckery#2](https://github.com/Plasma-Deckery/deckery/issues/2).
