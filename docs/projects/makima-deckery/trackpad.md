# Trackpad Emulation

!!! warning "Beta feature — not on `main`"
    Trackpad emulation lives on the `trackpad-config` branch of [makima-deckery](https://github.com/Plasma-Deckery/makima-deckery) and has not been merged to `main` yet. Config shape, device names, and behaviour described here can still change without notice. Don't rely on this for a production setup.

The Steam Deck trackpads are capable input surfaces, but Steam Input's default handling is invisible to gesture tools — they expect standard Linux multi-touch devices. Makima reads the trackpads' raw hidraw reports and translates them into proper MT events on virtual uinput devices, making both pads (and, optionally, a combined two-finger gesture surface) visible to tools like `libinput-gestures` or `fusuma`. This is the prerequisite for defining custom gestures per pad (swipe zones, tap areas, circular scroll, pinch-zoom) without implementing gesture recognition inside makima itself.

## Why hidraw, not evdev

The kernel driver (`hid-steam`) exposes trackpad position on evdev as `ABS_HAT0X/Y` (left) / `ABS_HAT1X/Y` (right), with clicks on `BTN_THUMB`/`BTN_THUMB2`. Earlier versions of this feature read position from evdev. That turned out to be the wrong source: evdev and hidraw are two different HID interfaces of the same physical device, read via two independent kernel/userspace paths, and they can arrive out of order relative to each other — combining "position from evdev" with "touch from hidraw" caused large cursor jumps on reposition.

Makima instead parses the raw 64-byte hidraw report directly (`pad_hidraw.rs`) and reads position, touch state, *and* click for both pads out of that single read. Because all of it comes from one `read()`, it's atomic by construction — there is no ordering bug possible, and no evdev fallback: if no hidraw sibling device is found for a controller, trackpad position/touch is simply unavailable (state.json will show pads as untouched, and MT-trackpad mode gets no input).

## Architecture

Trackpad handling is split into three layers, each independently testable and swappable:

```
pad_hidraw.rs        Raw producer. Parses hidraw reports into PadFrame{x, y,
                      touching, click} per pad and exposes a HapticCommand
                      sink for feature-report writes back to the device. No
                      knowledge of modes, gestures, or haptic policy — pure
                      HID wire-format decode/encode.

trackpad_router.rs    Core routing. Owned by EventReader, not by any handler.
                      Always mirrors raw position/touch/click into state.json
                      regardless of mode, tracks combined two-finger gesture-
                      session entry/exit (pad-order-independent), and routes
                      each frame to whichever per-channel handler input is
                      attached — left, right, and/or combined gesture.

handler modules       Interpreters downstream of the router. Each turns one
(mt_trackpad.rs,      channel's frame stream into virtual device events plus
gesture_pad.rs, ...)  its own haptic policy. Selected per pad via `mode` in
                      the config; a handler owns everything about "what this
                      mode feels like" and self-parses its own config shape.
```

This split exists so a new interpretation of the same raw pad data — a trackball-style relative-mouse mode, a radial/zone mode, different haptic timing — is a new handler module consuming the same `SinglePadFrame`/`CombinedPadFrame` stream, without touching the raw parser or the router.

### Layer 1 — `pad_hidraw.rs`: raw producer

Reads the controller's raw hidraw interface (the `.0005` sibling of the evdev gamepad node — found via sysfs, see `find_hidraw_for_evdev`) and, on every report, emits a `PadFrame`:

```rust
pub struct PadFrame {
    pub lx: i32, pub ly: i32, pub ltouch: bool, pub lclick: bool,
    pub rx: i32, pub ry: i32, pub rtouch: bool, pub rclick: bool,
}
```

Byte offsets were determined empirically by recording evdev and hidraw simultaneously against a shared monotonic clock. Position lives at fixed `i16` offsets in the report; touch and click for both pads are separate bits within the same status byte (`byte[10]`) — confirmed against the upstream `hid-steam` kernel driver's own bit layout.

This layer also owns the write side: haptic pulses ("click ticks", gesture feedback) are sent back to the device as HID feature reports (`HIDIOCSFEATURE`, report ID `0x8F`) via a `HapticCommand` channel. `HapticPad::{Left, Right, Both}` selects which actuator fires — its wire encoding was fixed empirically against real hardware (not read from kernel source alone, which described the opposite mapping).

Trackpad position/touch/click data and the Lizard Mode suppression heartbeat (see below) share this same raw hidraw file descriptor.

### Layer 2 — `trackpad_router.rs`: Core routing

Not spawned as its own task — called from `EventReader::run` inside the same `tokio::join!` as everything else, so it can borrow shared state (`PadState`, gesture-session flag) for its whole lifetime.

Two responsibilities, always active regardless of config:

1. **State export.** Every frame updates `PadState` (position, hardware touch, pressed) for both pads unconditionally — `state.json` reflects raw hardware truth even when a pad's `mode = "disabled"`, so the HUD can visualize trackpad input with no handler attached.
2. **Gesture-session tracking.** A pure, pad-order-independent state machine (`decide_gesture_transition`) decides whether a combined two-finger gesture session is active: it starts the instant *both* pads are simultaneously touching, and ends the instant *either* lifts — regardless of which pad touched down or lifted first. On exit, whichever pad is still touching gets a synthetic touch-down resume on its own individual channel, so a two-finger gesture that becomes one finger seamlessly continues as single-pad input instead of just stopping.

Beyond that, the router's only job is dispatch: forward each frame to whichever of `left_tx` / `right_tx` / `combined_tx` channels are `Some` (i.e. have a handler attached for that mode). A `None` channel is a disabled channel — the router skips sending into it entirely rather than blocking on a channel nobody is reading, so a pad set to `"disabled"` can never stall routing for the other pad.

`state.json` writes are rate-limited to ~60 Hz for analog movement, but bypass the limit entirely for digital transitions (touch lift/down, gesture enter/exit) so those are never delayed.

### Layer 3 — handler modules

A handler consumes one channel's frame stream (`SinglePadFrame` for an individual pad, `CombinedPadFrame` for the gesture channel) and decides what it *means*: which virtual device to emit MT events on, and what haptic feedback (if any) to fire and when. Selected per pad via `mode` in `[trackpad.left]` / `[trackpad.right]`.

| `mode` | Handler | Status |
|---|---|---|
| `"disabled"` | none | Default. No virtual device, no events forwarded. Position/touch/click still tracked into `state.json` by the router. |
| `"mt-trackpad"` | `mt_trackpad.rs` | Implemented. Emits standard MT touchpad events (`Deckery Left/Right Trackpad`), plus a haptic click-tick on click rising edge. |
| `"trackball"` | `trackball.rs` | **Stub only.** Accepted as a config value without warning, but no handler is actually wired into the router's `tokio::join!` — behaves identically to `"disabled"` today. Only its (currently empty) config struct exists, as a home for the shape once real relative-mouse behaviour lands. |
| `"scroll"` | `scroll_pad.rs` | **Stub only**, same status as `"trackball"` — module exists, nothing dispatches to it yet. |

The combined gesture channel (`[trackpad.gestures]`, enabled via `combined_gesture_device = true`) is handled separately by `gesture_pad.rs` — see below.

## Config ownership split

Config for a trackpad side is split between Core (`config.rs`) and the handler that `mode` selects, and each side only ever knows its own half:

- **Core owns `mode`** (which handler gets spawned) **and `click_pressure`** (a HID feature-report threshold that lives on the physical sensor itself — independent of whichever handler is active, since two handlers could never sensibly want different firmware thresholds at the same time), plus router-level settings like `combined_gesture_device`.
- **Everything else** in a `[trackpad.left]` / `[trackpad.right]` / `[trackpad.gestures]` table is handler-specific (haptics policy, movement algorithm, gesture semantics) and is hand to the handler as a raw, unparsed `toml::Value` — Core never learns or validates the shape. Each handler module defines its own `#[derive(Deserialize)]` struct and parses itself, falling back to defaults (with a logged warning) on any shape mismatch, so a typo in a handler-owned field can never crash makima or block input on the pad.

This is why `mt_trackpad::MtTrackpadConfig` and `gesture_pad::GesturePadConfig` exist as self-contained structs living in their own handler files instead of centralized in `config.rs`.

```toml
[trackpad.left]
mode = "mt-trackpad"        # Core: which handler to spawn
click_pressure = 30000      # Core: firmware click threshold (raw u16, optional)

[trackpad.left.haptic]
on_click = { duration_us = 2000, count = 1 }   # handler-owned: mt_trackpad's own config shape

[trackpad.right]
mode = "mt-trackpad"

[trackpad]
combined_gesture_device = true   # Core/router: enables the combined gesture channel

[trackpad.gestures.haptic]
on_gesture_start = { duration_us = 2000, count = 1 }   # handler-owned: gesture_pad's own config shape
```

The legacy `[settings] LPAD = "trackpad"` / `RPAD = "trackpad"` syntax is still accepted as a fallback that maps to `mode = "mt-trackpad"` when no `[trackpad.left]`/`[trackpad.right]` table is present.

## Virtual devices

| Device name | Created when | Source |
|---|---|---|
| `Deckery Left Trackpad` | `[trackpad.left] mode = "mt-trackpad"` | Left pad individual channel |
| `Deckery Right Trackpad` | `[trackpad.right] mode = "mt-trackpad"` | Right pad individual channel |
| `Deckery Combined Trackpad` | `[trackpad] combined_gesture_device = true` | Both pads, active only while a gesture session is active |

Position is Y-corrected to libinput convention (hardware reports up as negative; the virtual device flips this). On the combined device, left/right pads are split into left/right halves of a shared X axis so a pinch gesture tracks correctly across both MT slots. libinput derives everything it needs — two-finger scroll/pan, pinch-zoom — purely from the two `ABS_MT_POSITION` slots; there is no separate gesture-type event makima produces.

While a gesture session is active, individual pads seamlessly resume their own device the instant one finger lifts (see the router's gesture-transition logic above) — no gap, no re-touch-down needed by the user.

!!! note "Tap-to-click interaction with the combined device"
    If you enable `combined_gesture_device` and use quick two-hand gestures (e.g. pinch-zoom), disable "Tap to click" on the individual `Deckery Left/Right Trackpad` devices in your desktop's touchpad settings. Touching down with one pad slightly before the other briefly routes through that pad's individual channel before gesture mode activates; the router's forced clean-lift on gesture entry looks like a fast tap-and-release to libinput, which tap-to-click would otherwise turn into a spurious click.

## The combined gesture channel — `gesture_pad.rs`

The combined device isn't a distinct physical sensor — it has no `mode` or `click_pressure` of its own, so it doesn't get a `TrackpadSideConfig` like `left`/`right` do. Instead it's its own handler module with its own config shape, self-parsed from the raw `[trackpad.gestures]` table.

A click during a two-finger gesture has no established touchpad semantics (unlike a single-finger tap/click on an individual pad) — so unlike `mt_trackpad`'s `on_click`, there is deliberately **no click-based haptic** on the gesture channel. The physical click bit is still forwarded to the virtual device's `BTN_LEFT` unconditionally (same as a real multi-touch pad would report it), just with no haptic tied to it.

What *is* meaningful for a gesture is its lifecycle — start, ongoing movement, end — so `GestureHapticConfig` is keyed on that instead:

```toml
[trackpad.gestures.haptic]
on_gesture_start = { duration_us = 2000, count = 1 }   # fires when both pads become simultaneously touched
on_gesture_move   = { duration_us = 1000, count = 1 }   # fires repeatedly during movement — noisy if wired up naively
on_gesture_end    = { duration_us = 2000, count = 1 }   # fires when either pad lifts, ending the session
```

!!! note "Parsed, not wired up yet"
    None of the three lifecycle haptics fire yet. `gesture_pad::run` currently only sees a flat stream of `CombinedPadFrame`s, not session-transition events — recognising "session just started/ended" needs a signal from `trackpad_router`'s gesture-session tracking that isn't plumbed through to the handler yet. The config shape is settled and parses today; wiring the actual pulses is a follow-up.

## Haptic feedback

Both `mt_trackpad` (individual pads) and `gesture_pad` (combined channel) share the same underlying pulse mechanism (`mt_trackpad::pulse`) and wire format (`pad_hidraw::HapticCommand` → HID feature report `0x8F`), but each owns its *own* policy for when to fire:

- **`mt_trackpad`**: fires `on_click` on the rising edge of a physical click, per pad. Defaults to a short, quiet tick if unset.
- **`gesture_pad`**: fires on gesture lifecycle events (start/move/end) instead of click — see above. Not wired up yet.

Haptic parameters (`duration_us`, `interval_us`, `count`, `gain_db`) are identical across both — same `HapticPulse` struct — only the trigger condition differs per handler.

## State export

Trackpad position, touch state, and press state are always tracked and exported to `state.json` regardless of the `mode` setting for either pad — the HUD can visualize trackpad input even when both pads are `"disabled"`. See [State JSON](../../reference/state-json.md).

## Lizard Mode

Full Steam independence requires suppressing the `hid-steam` kernel driver's built-in mouse/scroll fallback ("Lizard Mode"), which otherwise emits mouse/scroll events directly from the trackpads, bypassing makima entirely. This is implemented — see `SUPPRESS_LIZARD_MODE` in [Configuration](../../configuration.md) — and shares the same raw hidraw file descriptor that `pad_hidraw.rs` uses for trackpad data.

## libinput tuning

When the virtual MT devices are registered, libinput applies its generic touchpad profile to them. Getting Steam Input-quality cursor feel (acceleration curve, trackball-style inertia) likely needs custom `libinput quirks` tuning for the Deckery devices specifically — not yet done. See [deckery#2](https://github.com/Plasma-Deckery/deckery/issues/2).

## Roadmap

| Status | Feature | Issue |
|---|---|---|
| ✅ | Virtual MT devices — expose raw trackpad data to the Linux input stack | — |
| ✅ | Lizard Mode suppression — hold the hidraw device open so the kernel driver doesn't override our output | [makima-deckery#11](https://github.com/Plasma-Deckery/makima-deckery/issues/11) |
| ✅ | Combined two-pad gesture device — both pads together as two fingers for pinch-zoom and pan | [deckery#7](https://github.com/Plasma-Deckery/deckery/issues/7) |
| ✅ | Haptic feedback — click-tick pulses via HID feature report, matching Steam's click-grid feel | [makima-deckery#9](https://github.com/Plasma-Deckery/makima-deckery/issues/9) |
| ✅ | Hardware settings via TOML — trackpad click-pressure threshold, per-mode haptic config | [makima-deckery#13](https://github.com/Plasma-Deckery/makima-deckery/issues/13) |
| ⏳ | Gesture-lifecycle haptics (`on_gesture_start`/`move`/`end`) — config parses, not wired to actual session transitions yet | — |
| ⏳ | Trackball / scroll handler modes — stub files exist (`trackball.rs`, `scroll_pad.rs`), not dispatched by the router | — |
| ⏳ | libinput device profile — tune acceleration curves and trackball inertia for Steam Input-quality cursor feel | [deckery#5](https://github.com/Plasma-Deckery/deckery/issues/5) |
| ⏳ | Gesture tool integration — discrete gesture zones trigger makima actions; continuous gestures go directly to the input stack | [deckery#3](https://github.com/Plasma-Deckery/deckery/issues/3) |
| ⏳ | Merge `trackpad-config` branch to `main` | — |
