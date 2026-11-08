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

## Muting a game in the background

```toml
[gaming_mode]
auto_mute = true   # built-in default: false; the shipped base config sets true
```

When `true`, a running Steam game is muted while its window does not have focus, and unmuted when it is focused again. Switch from a game to the desktop and it stops playing; switch back and it plays again.

- **Only the game.** Each audio stream is traced to its process and from there up to the game's `reaper` — the same walk the auto-detection above uses. Steam, browsers and voice chat are never touched.
- **It follows focus, not the Gaming Mode flag.** Toggling Gaming Mode by hand does not change the audio.
- **Only what Deckery muted is unmuted.** If you muted the game yourself, it stays muted when you switch back.
- **Turning the setting off releases a muted game immediately**; turning it on mutes a game that is already in the background.

One detail worth knowing if a game ever starts muted: WirePlumber remembers the mute state of every application by name and restores it the next time that application opens a stream. If a game exits while Deckery has it muted, WirePlumber would bring it back muted. Deckery therefore keeps a list of the application names whose remembered mute it caused — in `~/.local/state/deckery/auto-mute-names` — and releases such a stream when it reappears and there is no reason for it to be muted.

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

Gaming Mode state is reflected in `$XDG_RUNTIME_DIR/makima-state.json`:

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
