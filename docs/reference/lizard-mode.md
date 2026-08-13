# Lizard Mode Suppression — Reference

## Background

The `hid-steam` kernel driver keeps a built-in mouse/scroll fallback ("Lizard Mode") active unless a userspace client suppresses it. Steam handles this while running. Without suppression, the trackpads emit mouse and scroll events directly via the kernel driver, bypassing makima entirely.

## Heartbeat

Makima-deckery takes over suppression via a hidraw heartbeat. On startup, it opens the raw controller hidraw device (the `.0005` interface, not the emulated keyboard/mouse nodes) and sends suppression feature reports every 4 s. This shares the same file descriptor used by `pad_hidraw.rs` for trackpad data.

The heartbeat is a built-in safety mechanism: if makima crashes or exits, the file descriptor is closed and Lizard Mode re-activates automatically within ~8 s. No manual cleanup is required.

Makima gracefully skips the heartbeat task on non-Steam-Deck hardware (no Valve hidraw device found).

## Configuration

Control which aspects are suppressed via `SUPPRESS_LIZARD_MODE` in the `[settings]` section of your base config:

```toml
[settings]
SUPPRESS_LIZARD_MODE = "buttons,mouse"   # suppress both (recommended)
SUPPRESS_LIZARD_MODE = "buttons"          # only clear keyboard/button mappings
SUPPRESS_LIZARD_MODE = "mouse"            # only disable trackpad mouse/scroll emulation
SUPPRESS_LIZARD_MODE = "false"            # disabled (default when setting is absent)
```

| Value | Effect |
|---|---|
| `"buttons"` | Sends `ID_CLEAR_DIGITAL_MAPPINGS` (0x81) — prevents the kernel driver from emitting arrow keys, Enter, Esc via D-Pad and face buttons |
| `"mouse"` | Sends `ID_SET_SETTINGS_VALUES` (0x87) with `TRACKPAD_NONE` — prevents the kernel driver from emitting mouse and scroll events from the trackpads |
| `"buttons,mouse"` | Both of the above — recommended for full Steam independence |
| `"false"` / absent | Disabled — Lizard Mode is not suppressed |

When the setting is absent, Lizard Mode is **not** suppressed.
