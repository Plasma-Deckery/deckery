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
| `gain_db` | float | `0` | Gain offset in dB (optional) |
| `pause_ms` | integer | `0` | Pause after this step before the next (optional) |

## Where pulse chains are used

- **Gaming Mode** — `haptic_on` and `haptic_off` in `[gaming_mode]`. See [Gaming Mode reference](gaming-mode.md).
