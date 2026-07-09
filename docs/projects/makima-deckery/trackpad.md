# Trackpad Emulation

!!! warning "Beta feature — not on `main`"
    Trackpad emulation lives on the `trackpad-config` branch of [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) and has not been merged to `main` yet. Config shape, device names, and behaviour described here can still change without notice. Don't rely on this for a production setup.

The Steam Deck has two trackpads that can each track a single finger, but the OS can't read them individually — whatever Steam Input does with them under the hood is invisible to every other tool. What we can do instead is read both trackpads ourselves and emulate standard Linux trackpad devices from them. That means, for example, the right trackpad can act as a completely normal mouse.

## Virtual devices

The virtual devices are configured per pad. Here's the right trackpad acting as a mouse, with the left trackpad left off:

```toml
[trackpad.right]
mode = "mt-trackpad"   # right trackpad acts as a standard mouse/trackpad

[trackpad.left]
mode = "disabled"       # default — left trackpad stays off
```

!!! note "Tap-to-click"
    If you use the right (or left) trackpad as a mouse, disable "Tap to click" on the `Deckery Right/Left Trackpad` device in your desktop's touchpad settings if you don't want a light tap to register as a click.

## Combined trackpad

What Deckery does that Steam Input can't: both trackpads combine into a single multi-touch surface, enabling real two-finger gestures — two-thumb scroll and pinch-to-zoom — across both pads at once. That gets you very smooth horizontal and vertical scrolling and very smooth zooming, e.g. for comfortably navigating a canvas — noticeably better than the scroll wheel emulation Steam offers.

```toml
[trackpad.left]
mode = "mt-trackpad"

[trackpad.right]
mode = "mt-trackpad"

[trackpad]
combined_gesture_device = true   # combines both pads into one gesture surface
```

Individual pads seamlessly resume their own device the instant one finger lifts out of a two-finger gesture — no gap, no re-touch-down needed.

!!! note "Tap-to-click and the combined device"
    Touching down with one pad slightly before the other briefly routes through that pad's individual device before the combined gesture kicks in, and can register as a spurious click if "Tap to click" is enabled on the individual `Deckery Left/Right Trackpad` devices. Disable it there if you use quick two-hand gestures like pinch-zoom.

## Haptic feedback

Each click or gesture transition can fire a haptic pulse via the trackpad's actuators:

| Field | Location | Fires on |
|---|---|---|
| `haptic.on_click` | `[trackpad.left]` / `[trackpad.right]` | Physical click on that pad (rising edge). Omit for a conservative built-in default. |
| `haptic.on_gesture_start` | `[trackpad.gestures]` | Combined gesture session starting (both pads touched at once). Not wired up yet. |
| `haptic.on_gesture_move` | `[trackpad.gestures]` | Combined gesture in progress. Not wired up yet. |
| `haptic.on_gesture_end` | `[trackpad.gestures]` | Combined gesture session ending (either pad lifts). Not wired up yet. |

Each pulse accepts `duration_us`, `interval_us`, `count`, and `gain_db`:

```toml
[trackpad.right.haptic]
on_click = { duration_us = 2000, count = 1 }
```

See [Trackpad Architecture](../../reference/trackpad-architecture.md) under Development for how this is implemented internally.

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
