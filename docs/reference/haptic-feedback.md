# Haptic Feedback — Reference

Makima drives the Steam Deck's trackpad actuators directly via hidraw. Haptic output is configured as a **pulse chain** — an array of steps, each describing a burst of pulses.

## Pulse chain format

```toml
haptic_on = [
    { duration_us = 8000, interval_us = 8000, count = 1, pause_ms = 150 },
    { duration_us = 8000, interval_us = 8000, count = 1 },
]
```

Each step in the chain:

| Field | Type | Default | Description |
|---|---|---|---|
| `duration_us` | integer | — | Pulse duration in microseconds |
| `interval_us` | integer | — | Interval between pulses in microseconds |
| `count` | integer | — | Number of pulses in this step |
| `gain_db` | integer | `0` | Gain offset in dB (optional). Accepted, but has no perceptible effect on Steam Deck hardware. |
| `pause_ms` | integer | `0` | Pause after this step before the next (optional) |

## Where pulse chains are used

- **Gaming Mode** — `haptic_on` and `haptic_off` in `[gaming_mode]`. See [Gaming Mode reference](gaming-mode.md).
- **Trackpads** — `on_press`, `on_release` and `on_movement` in `[trackpad.left.haptic]` and `[trackpad.right.haptic]`; `on_gesture_start`, `on_gesture_move` and `on_gesture_end` in `[trackpad.gestures.haptic]`. See `configs/Steam Deck Trackpads.toml` for a worked example.
- **Any binding** — `haptic = { … }` on a `[remap]` or `[commands]` entry plays when that binding fires; the shipped config uses it for the mouse clicks on L2 and R2. See [Bindings](../projects/makima-deckery/bindings.md#haptic).
