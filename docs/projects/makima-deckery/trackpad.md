# Trackpad Emulation

!!! warning "Beta feature — not on `main`"
    Trackpad emulation lives on the `trackpad-config` branch of [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) and has not been merged to `main` yet.

The Steam Deck has two trackpads that can each track a single finger, but the OS has no direct way to read them individually — whatever Steam Input does with the raw hardware is invisible to every other piece of software running on the system. Without Steam in the loop, that hardware is effectively unusable from the desktop.

Makima solves this by reading both trackpads itself, directly from the hardware, and turning them into standard Linux input devices. That means, for example, the right trackpad can act as a completely normal mouse. Once emulated, a trackpad registers with the system exactly like any other trackpad — the desktop environment sees an ordinary input device, configurable through the same touchpad settings panel as a laptop trackpad (pointer speed, tap-to-click, scrolling, and so on).

## Virtual Trackpads

Each pad is configured independently under `[trackpad.left]` / `[trackpad.right]`:

```toml
[trackpad.right]
mode = "mt-trackpad"       # right trackpad acts as a standard mouse/trackpad
click_pressure = 30000     # optional: firmware click-pressure threshold (raw u16, omit for firmware default)

[trackpad.right.kde]
pointer_acceleration         = 0.2      # cursor speed within the chosen profile (-1.0..+1.0)
pointer_acceleration_profile = "flat"   # "flat" (1:1, recommended) or "adaptive" (KDE default)

[trackpad.right.haptic]
on_press    = { duration_us = 8000, interval_us = 8000, count = 3, gain_db = 0 }   # fires when the finger presses down
on_release  = { duration_us = 8000, interval_us = 8000, count = 3, gain_db = 0 }   # fires when the finger lifts off the click
# on_movement = { pixel_interval = 3000, duration_us = 4000, interval_us = 4000, count = 1, gain_db = 0 }

[trackpad.left]
mode = "disabled"          # default — left trackpad stays off
```

| Field | Default | Meaning |
|---|---|---|
| `mode` | `"disabled"` | See [Trackpad modes](#trackpad-modes) below. |
| `click_pressure` | firmware default | Physical click threshold, as a raw firmware value. Optional. |
| `kde.pointer_acceleration` | `0.2` | Cursor speed multiplier within the chosen profile. Range −1.0 (slowest) to +1.0 (fastest). |
| `kde.pointer_acceleration_profile` | `"flat"` | `"flat"` for 1:1 movement (recommended — consistent and predictable on a small pad surface); `"adaptive"` for the libinput default (slows slow movements, amplifies fast ones). |
| `kde.tap_to_click` | `false` | Whether a light tap registers as a click. Disabled by default — accidental taps occur when switching between gesture mode and cursor mode. |
| `kde.disable_while_typing` | `false` | Suppresses trackpad input while the keyboard is active. Disabled by default — not useful in a gaming context. |
| `haptic.on_press` | 3-pulse burst | Haptic pulse fired on the press edge of a physical click. |
| `haptic.on_release` | 3-pulse burst | Haptic pulse fired on the release edge of a physical click. |
| `haptic.on_movement` | — (silent) | Pulse fired per `pixel_interval` raw units of cursor travel. `pixel_interval` defaults to 3000 (≈2mm). Silent by default — enable explicitly if you want a trackpad-click-wheel feel. |

Haptic pulses take four fields, each with its own default if omitted:

| Field | Default | Meaning |
|---|---|---|
| `duration_us` | `8000` | Pulse length in microseconds. |
| `interval_us` | `8000` | Gap between repeated pulses, in microseconds. |
| `count` | `3` | Number of pulses fired. |
| `gain_db` | `0` | Pulse loudness/strength adjustment, in dB. |

The default is a three-pulse burst (8ms on / 8ms off), tuned on real hardware against the Lizard Mode click buzz as a reference feel. Both edges fire the same tuned burst by default — a physical click is really two separate feelable edges, not one event.

## Combined Trackpad

What Deckery does that Steam Input can't: both trackpads combine into a single multi-touch surface, enabling real two-finger gestures — two-thumb scroll and pinch-to-zoom — across both pads at once. That gets you very smooth horizontal and vertical scrolling and very smooth zooming, e.g. for comfortably navigating a canvas — noticeably better than the scroll wheel emulation Steam offers.

```toml
[trackpad.left]
mode = "disabled"

[trackpad.right]
mode = "mt-trackpad"

[trackpad]
combined_gesture_device = true   # combines both pads into one gesture surface

[trackpad.gestures.kde]
natural_scroll = true    # content follows the finger — standard for two-finger scrolling
scroll_factor  = 0.5     # scrolls at half speed (raw pad range ±32767 makes the default too fast)
```

The `[trackpad.gestures.kde]` block is optional — the values above are the defaults that apply even if the block is absent.

### Haptic feedback

Rather than click, the combined device fires on the gesture's lifecycle — start, ongoing movement, and end — since a click has no established meaning mid-gesture:

```toml
[trackpad.gestures.haptic]
on_gesture_start = { duration_us = 2000, interval_us = 0, count = 1, gain_db = 0 }   # both pads become touched at once
on_gesture_move  = { pixel_interval = 3000, duration_us = 1000, interval_us = 0, count = 1, gain_db = 0 }   # per pixel_interval units of movement
on_gesture_end   = { duration_us = 2000, interval_us = 0, count = 1, gain_db = 0 }   # either pad lifts, ending the session
```

All three are silent by default — gesture haptics have no established reference feel to fall back to, unlike a physical click edge.

## Trackpad modes

Set per pad via `mode` in `[trackpad.left]` / `[trackpad.right]`:

| Mode | Status | Description |
|---|---|---|
| `disabled` | ✅ Available (default) | Pad is off — no virtual device. Position is still tracked internally for the HUD. |
| `mt-trackpad` | ✅ Available | Standard Linux multi-touch trackpad, as used throughout this page. Circular scrolling (swipe around the pad's edge to scroll) is planned as an option here. |
| `trackball` | ⏳ Planned | Cursor moves as a trackball — relative motion with momentum, closer to Steam Input's trackball feel, instead of absolute position. |
| `scroll` | ⏳ Planned | Pad dedicated to scrolling only. |

See [Trackpad Architecture](../../reference/trackpad-architecture.md) under Development for how this is implemented internally.

## Roadmap

| Status | Feature | Issue |
|---|---|---|
| ✅ | Virtual MT devices — expose raw trackpad data to the Linux input stack | — |
| ✅ | Lizard Mode suppression — hold the hidraw device open so the kernel driver doesn't override our output | [makima-deckery#11](https://github.com/Plasma-Deckery/makima-deckery/issues/11) |
| ✅ | Combined two-pad gesture device — both pads together as two fingers for pinch-zoom and pan | [deckery#7](https://github.com/Plasma-Deckery/deckery/issues/7) |
| ✅ | Haptic feedback — click-tick pulses, matching Steam's click-grid feel | [makima-deckery#9](https://github.com/Plasma-Deckery/makima-deckery/issues/9) |
| ✅ | Hardware settings via TOML — click-pressure threshold, per-mode haptic config | [makima-deckery#13](https://github.com/Plasma-Deckery/makima-deckery/issues/13) |
| ✅ | Movement haptics — `on_movement` pulse fires per distance traveled, not per time | [makima-deckery#22](https://github.com/Plasma-Deckery/makima-deckery/issues/22) |
| ✅ | Gesture-lifecycle haptics — `on_gesture_start`/`on_gesture_move`/`on_gesture_end` | — |
| ✅ | libinput defaults — `[trackpad.*.kde]` writes kcminputrc on startup (tap-to-click off, flat acceleration, scroll tuning) | [makima-deckery#25](https://github.com/Plasma-Deckery/makima-deckery/issues/25) |
| ⏳ | Trackball / scroll pad modes | — |
| ⏳ | Gesture tool integration — discrete gesture zones trigger makima actions; continuous gestures go directly to the input stack | [deckery#3](https://github.com/Plasma-Deckery/deckery/issues/3) |
| ⏳ | Merge `trackpad-config` branch to `main` | — |
