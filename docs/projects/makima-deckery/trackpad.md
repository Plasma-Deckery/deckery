# Trackpad Emulation

!!! info "On `main`, not yet in a release"
    Trackpad emulation has been merged to `main` on [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) but has not appeared in a tagged release yet. Build from source or use the Deckery install script to get it.

The Steam Deck has two trackpads that can each track a single finger, but the OS has no direct way to read them individually — whatever Steam Input does with the raw hardware is invisible to every other piece of software running on the system. Without Steam in the loop, that hardware is effectively unusable from the desktop.

Makima solves this by reading both trackpads itself, directly from the hardware, and turning them into standard Linux input devices. That means, for example, the right trackpad can act as a completely normal mouse. Once emulated, a trackpad registers with the system exactly like any other trackpad — the desktop environment sees an ordinary input device, configurable through the same touchpad settings panel as a laptop trackpad (pointer speed, tap-to-click, scrolling, and so on).

## Virtual Trackpads

Each pad is configured independently under `[trackpad.left]` / `[trackpad.right]`:

```toml
[trackpad.right]
mode = "mt-trackpad"       # right trackpad acts as a standard mouse/trackpad
click_pressure = 30000     # optional: firmware click-pressure threshold (raw u16, omit for firmware default)
# pixel_interval = 3000    # optional: raw units of travel per on_movement tick

[trackpad.right.kde]
pointer_acceleration         = 0.2      # cursor speed within the chosen profile (-1.0..+1.0)
pointer_acceleration_profile = "flat"   # "flat" (1:1, recommended) or "adaptive" (KDE default)

[trackpad.right.haptic]
on_press    = { duration_us = 8000, interval_us = 8000, count = 3, gain_db = 0 }   # fires when the finger presses down
on_release  = { duration_us = 8000, interval_us = 8000, count = 3, gain_db = 0 }   # fires when the finger lifts off the click
# on_movement = { duration_us = 4000, interval_us = 4000, count = 1, gain_db = 0 }

[trackpad.left]
mode = "disabled"          # default — left trackpad stays off
```

| Field | Default | Meaning |
|---|---|---|
| `mode` | `"disabled"` | See [Trackpad modes](#trackpad-modes) below. |
| `click_pressure` | firmware default | Physical click threshold, as a raw firmware value. Optional. |
| `pixel_interval` | `3000` | Raw units of cursor travel (≈2mm) per `haptic.on_movement` tick. |
| `kde.pointer_acceleration` | `0.2` | Cursor speed multiplier within the chosen profile. Range −1.0 (slowest) to +1.0 (fastest). |
| `kde.pointer_acceleration_profile` | `"flat"` | `"flat"` for 1:1 movement (recommended — consistent and predictable on a small pad surface); `"adaptive"` for the libinput default (slows slow movements, amplifies fast ones). |
| `kde.tap_to_click` | `false` | Whether a light tap registers as a click. Disabled by default — accidental taps occur when switching between gesture mode and cursor mode. |
| `kde.disable_while_typing` | `false` | Suppresses trackpad input while the keyboard is active. Disabled by default — not useful in a gaming context. |
| `haptic.on_press` | 3-pulse burst | Haptic fired on the press edge of a physical click. `false` silences it. |
| `haptic.on_release` | 3-pulse burst | Haptic fired on the release edge of a physical click. `false` silences it. |
| `haptic.on_movement` | — (silent) | Haptic fired per `pixel_interval` raw units of cursor travel. Silent by default — enable explicitly (`true` is one short tick) if you want a trackpad-click-wheel feel. |

Every haptic value takes the same form as a binding's [`haptic =`](bindings.md#haptic), without `pad` — the section already decides the pad. Either a single event, or a list of steps with an optional `pause_ms` after each:

```toml
on_press   = { duration_us = 8000, count = 3 }
on_release = [{ duration_us = 8000, count = 1, pause_ms = 40 }, { duration_us = 4000, count = 1 }]
```

What decides *when* a movement tick fires (`pixel_interval`) is a key of the pad section, never of the haptic. A haptic still written in the old flat form with `pixel_interval` inside it is ignored with a warning.

Each event takes four fields, each with its own default if omitted:

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
[trackpad.gestures]
pixel_interval = 3000   # raw units of movement (both fingers summed) per on_gesture_move tick

[trackpad.gestures.haptic]
on_gesture_start = { duration_us = 2000, interval_us = 0, count = 1, gain_db = 0 }   # both pads become touched at once
on_gesture_move  = { duration_us = 1000, interval_us = 0, count = 1, gain_db = 0 }   # per pixel_interval units of movement
on_gesture_end   = { duration_us = 2000, interval_us = 0, count = 1, gain_db = 0 }   # either pad lifts, ending the session
```

All three are silent by default — gesture haptics have no established reference feel to fall back to, unlike a physical click edge. They take the same single-event-or-list form as the pad haptics above.

## Trackpad modes

Set per pad via `mode` in `[trackpad.left]` / `[trackpad.right]`:

| Mode | Status | Description |
|---|---|---|
| `disabled` | ✅ Available (default) | Pad is off — no virtual device. Position is still tracked internally for the HUD. |
| `mt-trackpad` | ✅ Available | Standard Linux multi-touch trackpad, as used throughout this page. Circular scrolling (swipe around the pad's edge to scroll) is planned as an option here. |
| `trackball` | ✅ Available | Cursor moves as a trackball — relative motion with momentum, like Steam Input's trackball option. See [Trackball Mode](#trackball-mode). |
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
| ✅ | Trackball mode — relative pointer motion with momentum, see below | — |
| ⏳ | Gesture tool integration — discrete gesture zones trigger makima actions; continuous gestures go directly to the input stack | [deckery#3](https://github.com/Plasma-Deckery/deckery/issues/3) |
| ✅ | Merge `trackpad-config` branch to `main` | — |

## Trackball Mode

`mode = "trackball"` turns a pad into the ball of a trackball, the way Steam Input's trackball option does:

- **Dragging** moves the pointer by the finger's movement, scaled by `sensitivity`.
- **Flicking** sets the ball rolling. On lift, the release velocity is the finger's average speed over the last 50 ms before the lift; if it is at least `min_fling_speed`, the pointer keeps moving in that direction. A finger that stopped before lifting does not fling.
- **Decay** is exponential: `v(t) = v0 · e^(−friction · t)`. The ball stops once its speed falls below `stop_speed`. A fling travels about `v0 / friction` raw units in total; with `friction = 0` it rolls until touched.
- **Touching the pad stops the ball** where it is, and moving from there carries on without a jump.
- The **physical click** is `BTN_LEFT`. `click_pressure` applies as in `mt-trackpad`.

The output is relative pointer motion (`REL_X`/`REL_Y`) on the shared **Makima Virtual Pointer** device — the same device `RSTICK = "cursor"` writes to — not a per-pad multi-touch trackpad. So the `[trackpad.<side>.kde]` settings, which target the `Deckery Left/Right Trackpad` devices, do not apply to a trackball pad. When a two-finger gesture or Gaming Mode takes the pad away mid-touch, the ball stops without flinging and a held click is released.

```toml
[trackpad.right]
mode            = "trackball"
sensitivity     = 0.008   # pointer pixels per raw pad unit
friction        = 2.0     # decay rate per second; 0 rolls until touched
min_fling_speed = 40000   # raw units/s at lift needed to set the ball rolling
stop_speed      = 1500    # raw units/s below which the ball stops
grid            = 7       # cells per pad side, for drag and roll ticks

[trackpad.right.haptic]
on_press    = { duration_us = 8000, interval_us = 8000, count = 3, gain_db = 0 }
on_release  = { duration_us = 8000, interval_us = 8000, count = 3, gain_db = 0 }
on_roll     = { duration_us = 4000, interval_us = 4000, count = 1, gain_db = 0 }   # tick per grid cell while rolling
on_movement = { duration_us = 4000, interval_us = 4000, count = 1, gain_db = 0 }   # tick per grid cell while dragging
```

These are tested values; the shipped `Steam Deck Trackpads.toml` carries the same block, commented out.

| Field | Unit | Default | Meaning |
|---|---|---|---|
| `sensitivity` | pointer pixels per raw pad unit | `0.02` | Scale for dragging and rolling alike. The pad is 65 536 raw units per axis, so `0.02` is about 1 300 px per full swipe. Must be above 0. |
| `friction` | 1/s | `4.0` | Exponential decay rate of a rolling ball. Higher stops sooner; `0` never slows. Must be at least 0. |
| `min_fling_speed` | raw units/s | `40000` | Finger speed at lift needed to set the ball rolling. Below it, a lift just stops. Must be at least 0. |
| `stop_speed` | raw units/s | `1500` | Speed below which a rolling ball stops. Must be above 0, since an exponential decay never reaches 0 on its own. Also a lower bound for flinging. |
| `grid` | cells per pad side | `8` | Detent raster for `on_movement` and `on_roll`: the pad is split into `grid` × `grid` cells (each `65536 / grid` raw units wide). Whole number from 1 to 65 536. |
| `click_pressure` | raw u16 | firmware default | Physical click threshold, as in `mt-trackpad`. |

Velocities are measured in raw pad units, not pixels, so whether a flick flings does not change with `sensitivity`. Every key is optional and parsed on its own: an invalid value or an unknown key logs a warning, and that key falls back to its default while the others stay as written.

### The grid

A real trackball has one detent spacing, so dragging and rolling share one raster. A tick fires each time the position crosses into a new cell. A cell is only left once the position is 0.1 cell past its edge, so a finger resting on a boundary does not buzz. While rolling, the ball keeps a virtual position that continues from where the finger lifted, so the raster carries on across the lift without an extra tick, and the tick rate follows the ball's speed as it slows. Roll ticks are capped at one per 8 ms roll step.

### Haptics

`[trackpad.<side>.haptic]` in trackball mode takes these keys:

| Key | Default | Fires |
|---|---|---|
| `on_press` | 3-pulse burst | On the press edge of a physical click. |
| `on_release` | 3-pulse burst | On the release edge of a physical click. |
| `on_movement` | — (silent) | Once per grid cell the finger drags into. `true` switches on one short tick (`4000 µs`, count 1). |
| `on_roll` | one short tick | Once per grid cell the rolling ball moves into. |

`false` silences any of them. Each value takes the same form as the other pad haptics: a single event, or a list of steps with an optional `pause_ms` after each (see [Virtual Trackpads](#virtual-trackpads)). The tick spacing is `grid` in the pad section, never inside the haptic; a haptic that still carries `grid` or `pixel_interval` inside it is ignored with a warning and that key uses its default.
