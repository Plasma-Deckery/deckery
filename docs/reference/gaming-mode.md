# Gaming Mode — Reference

## Trigger configuration

```toml
[gaming_mode]
trigger = { key = "BTN_BASE", ms = 400 }
```

| Field | Default | Description |
|---|---|---|
| `key` | `"BTN_BASE"` | Button to double-press. Any evdev key name. Set to `"disabled"` to turn off the trigger entirely. |
| `ms` | `400` | Maximum time between the two presses in milliseconds. |

In pause/preview mode the double-click is still detected and writes `last_action` so the HUD preview can show the action — but Gaming Mode is not actually toggled and haptics do not fire.

## Auto-detection

```toml
[gaming_mode]
auto_detect_steam_games = true   # default
```

When `true`, Gaming Mode activates automatically when a Steam game is detected as the focused window, and deactivates when focus moves away.

Detection uses two signals — either is sufficient:

- **Steam Big Picture Mode** — focused window has class `"steam"` and a caption containing `"Big Picture"` or `"Big-Picture"`.
- **Steam game process** — the focused window's PID is a descendant of `reaper`, whose parent is `steam`. This is the process tree structure Steam uses for every launched game (native, Proton, Wine, bwrap, etc.). Makima walks `/proc/{pid}/status` upward from the focused PID — typically 3–7 files, under 1 ms.

Set to `false` to disable. Gaming Mode can then only be toggled via the double-click trigger or IPC.

## Haptic feedback

`haptic_on` fires when Gaming Mode turns **on**; `haptic_off` fires when it turns **off**. Both have sensible built-in defaults and do not need to be set in the config.

For the pulse chain format and all available fields, see [Haptic Feedback](haptic-feedback.md).

## IPC commands

```bash
echo "gaming_mode enable"  | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
echo "gaming_mode disable" | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/makima-control.sock
```

See [IPC](ipc.md) for the full command reference.

## `while_gaming` bindings

By default, all bindings are suppressed while Gaming Mode is active. Bindings tagged `while_gaming = true` opt out of that suppression — they remain active in Gaming Mode and also continue to work normally in desktop use.

```toml
[commands]
BTN_THUMBL = { run = ["deckery-hud-toggle"], no_pause = true, while_gaming = true, label = "Toggle HUD" }
```

## State export

Gaming Mode state is reflected in `/tmp/makima-state.json`:

```json
{
  "context": {
    "gaming_mode": true
  },
  "gaming_mode_trigger": {
    "key":   "BTN_BASE",
    "label": "Toggle Gaming Mode"
  }
}
```

`gaming_mode_trigger` is `null` when `trigger = { key = "disabled" }`.

See [State JSON](state-json.md) for the full schema.
