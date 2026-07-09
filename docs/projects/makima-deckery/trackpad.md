# Trackpad Emulation

!!! warning "Beta feature — not on `main`"
    Trackpad emulation lives on the `trackpad-config` branch of [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) and has not been merged to `main` yet. Config shape, device names, and behaviour described here can still change without notice. Don't rely on this for a production setup.

The Steam Deck trackpads are capable input surfaces, but Steam Input's default handling is invisible to gesture tools — they expect standard Linux multi-touch devices. Makima reads both trackpads directly and exposes them as virtual MT (multi-touch) devices, making them visible to tools like `libinput-gestures` or `fusuma`. This is the prerequisite for defining custom gestures per pad (swipe zones, tap areas, circular scroll, pinch-zoom) and for a combined two-finger gesture surface (pinch-zoom, two-finger scroll/pan) across both pads at once.

For how this is implemented internally, see [Trackpad Architecture](../../reference/trackpad-architecture.md) under Development.

## Virtual devices

| Device name | Created when | Source |
|---|---|---|
| `Deckery Left Trackpad` | `[trackpad.left] mode = "mt-trackpad"` | Left pad |
| `Deckery Right Trackpad` | `[trackpad.right] mode = "mt-trackpad"` | Right pad |
| `Deckery Combined Trackpad` | `[trackpad] combined_gesture_device = true` | Both pads, active only while both are touching at once (e.g. pinch-zoom) |

Individual pads seamlessly resume their own device the instant one finger lifts out of a two-finger gesture — no gap, no re-touch-down needed.

Trackpad position, touch state, and press state are always tracked and exported to `state.json` regardless of the `mode` setting — the HUD can visualize trackpad input even when a pad is `"disabled"`.

## Configuration

```toml
[trackpad.left]
mode = "mt-trackpad"        # creates "Deckery Left Trackpad"
click_pressure = 30000      # optional: firmware click-pressure threshold (raw u16)

[trackpad.left.haptic]
on_click = { duration_us = 2000, count = 1 }   # haptic "click tick" on physical click

[trackpad.right]
mode = "mt-trackpad"        # creates "Deckery Right Trackpad"

[trackpad]
combined_gesture_device = true   # also creates "Deckery Combined Trackpad" for two-finger gestures

[trackpad.gestures.haptic]
on_gesture_start = { duration_us = 2000, count = 1 }   # not wired up yet — see Trackpad Architecture
```

| Setting | Location | Meaning |
|---|---|---|
| `mode` | `[trackpad.left]` / `[trackpad.right]` | `"disabled"` (default) — no virtual device, position still tracked · `"mt-trackpad"` — standard MT touchpad device |
| `click_pressure` | `[trackpad.left]` / `[trackpad.right]` | Optional firmware click threshold. Omit for firmware default. |
| `haptic.on_click` | `[trackpad.left]` / `[trackpad.right]` | Haptic pulse fired on physical click (rising edge). Omit for a conservative built-in default. |
| `combined_gesture_device` | `[trackpad]` | `true` enables the combined two-finger gesture device. |
| `haptic.on_gesture_start` / `on_gesture_move` / `on_gesture_end` | `[trackpad.gestures]` | Haptic pulses for the gesture lifecycle instead of click (a click mid-gesture has no established meaning). Config parses today; not yet wired to actual pulses. |

Each `haptic.*` pulse accepts `duration_us`, `interval_us`, `count`, and `gain_db`.

The legacy `[settings] LPAD = "trackpad"` / `RPAD = "trackpad"` syntax is still accepted as a fallback for `mode = "mt-trackpad"`.

!!! note "Tap-to-click interaction with the combined device"
    If you enable `combined_gesture_device` and use quick two-hand gestures (e.g. pinch-zoom), disable "Tap to click" on the individual `Deckery Left/Right Trackpad` devices in your desktop's touchpad settings. Touching down with one pad slightly before the other briefly routes through that pad's individual channel before gesture mode activates, and can otherwise register as a spurious click.

## Lizard Mode

Full Steam independence requires suppressing the `hid-steam` kernel driver's built-in mouse/scroll fallback ("Lizard Mode"), which otherwise emits mouse/scroll events directly from the trackpads, bypassing makima entirely. See `SUPPRESS_LIZARD_MODE` in [Configuration](../../configuration.md).

## Roadmap

| Status | Feature | Issue |
|---|---|---|
| ✅ | Virtual MT devices — expose raw trackpad data to the Linux input stack | — |
| ✅ | Lizard Mode suppression — hold the hidraw device open so the kernel driver doesn't override our output | [makima-deckery#11](https://github.com/Plasma-Deckery/makima-deckery/issues/11) |
| ✅ | Combined two-pad gesture device — both pads together as two fingers for pinch-zoom and pan | [deckery#7](https://github.com/Plasma-Deckery/deckery/issues/7) |
| ✅ | Haptic feedback — click-tick pulses, matching Steam's click-grid feel | [makima-deckery#9](https://github.com/Plasma-Deckery/makima-deckery/issues/9) |
| ✅ | Hardware settings via TOML — click-pressure threshold, per-mode haptic config | [makima-deckery#13](https://github.com/Plasma-Deckery/makima-deckery/issues/13) |
| ⏳ | Gesture-lifecycle haptics (`on_gesture_start`/`move`/`end`) — config parses, pulses not wired up yet | — |
| ⏳ | Trackball / scroll pad modes | — |
| ⏳ | libinput device profile — tune acceleration curves and trackball inertia for Steam Input-quality cursor feel | [deckery#5](https://github.com/Plasma-Deckery/deckery/issues/5) |
| ⏳ | Gesture tool integration — discrete gesture zones trigger makima actions; continuous gestures go directly to the input stack | [deckery#3](https://github.com/Plasma-Deckery/deckery/issues/3) |
| ⏳ | Merge `trackpad-config` branch to `main` | — |
