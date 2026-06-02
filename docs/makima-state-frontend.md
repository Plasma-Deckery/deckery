# Makima State — Frontend Integration Guide

## Overview

Makima writes `/tmp/makima-state.json` atomically after every relevant input event.
The file is updated via `rename()` so reads are always consistent — no partial writes.

Watch for changes using inotify on the **directory**, not the file itself (atomic rename
creates a new inode each time, so watching the file directly loses events):

```bash
inotifywait -m -e moved_to /tmp/ | grep --line-buffered "makima-state.json"
```

---

## Full Schema

```json
{
  "context": {
    "config_stack": ["Steam Deck"],
    "layout": 0,
    "paused": false,
    "held_modifiers": ["BTN_TL"],
    "active_buttons": ["BTN_TL", "BTN_SOUTH"]
  },
  "bindings": {
    "BTN_SOUTH": { "action": ["KEY_ENTER"], "origin": "Steam Deck" },
    "BTN_TL-BTN_GRIPR2": { "action": ["KEY_LEFTCTRL", "KEY_PAGEDOWN"], "origin": "Steam Deck" }
  },
  "modifier_active": {
    "BTN_GRIPR2": { "action": ["KEY_LEFTCTRL", "KEY_PAGEDOWN"], "origin": "Steam Deck" }
  },
  "last_event": {
    "input": "BTN_SOUTH",
    "action": ["KEY_ENTER"],
    "kind": "remap",
    "value": 1
  },
  "trackpads": {
    "lpad": {
      "mode": "trackpad",
      "x": 1234,
      "y": -567,
      "touching": true,
      "pressed": false
    },
    "rpad": {
      "mode": "trackpad",
      "x": 0,
      "y": 0,
      "touching": false,
      "pressed": false
    }
  }
}
```

---

## Fields

### `context`

| Field | Type | Meaning |
|---|---|---|
| `config_stack` | `[string]` | Active config name(s). Currently always one entry. |
| `layout` | `number` | Active layout index (0–3). For future multi-layout support. |
| `paused` | `bool` | Makima is paused — no output is emitted. Set when HUD opens. |
| `held_modifiers` | `[string]` | Modifier buttons currently physically held (e.g. `["BTN_TL"]`). Empty when no modifier is held. **Use this to switch between normal and modifier view.** |
| `active_buttons` | `[string]` | All buttons currently physically held, including non-modifiers (e.g. `["BTN_TL", "BTN_SOUTH"]`). **Use this to highlight buttons on the gamepad layout.** |

---

### `bindings`

Complete map of all configured button actions for the current config.

Key format:
- `"BTN_SOUTH"` — plain binding, no modifier
- `"BTN_TL-BTN_GRIPR2"` — combo: BTN_TL held, BTN_GRIPR2 pressed

Value:
```json
{ "action": ["KEY_ENTER"], "origin": "Steam Deck" }
```

- `action`: list of output keys that get emitted
- `origin`: config name this binding comes from

**This map is static while the config doesn't change.** Reload it when `context.config_stack` changes.

---

### `modifier_active`

Subset of `bindings` — only the combos reachable with the currently held modifiers.

Key format: just the trigger button name (modifier prefix stripped), e.g. `"BTN_GRIPR2"`.

Value: same shape as `bindings`.

Empty `{}` when no modifier is held.

**Use this to replace `bindings` in the display when `held_modifiers` is non-empty.**
The frontend does not need to filter `bindings` manually — makima does it.

---

### `trackpads`

Present when `LPAD` or `RPAD` is set to `"trackpad"` in the config.
Always contains both `lpad` and `rpad` entries.

| Field | Type | Meaning |
|---|---|---|
| `mode` | `string` | `"trackpad"` or `"disabled"` — value of `LPAD`/`RPAD` setting |
| `x` | `number` | Raw X position, range −32767…32767. `0` when not touching. |
| `y` | `number` | Raw Y position, range −32767…32767. `0` when not touching. Positive = up (hardware convention). |
| `touching` | `bool` | `true` when finger is on the pad (`x != 0 \|\| y != 0`). |
| `pressed` | `bool` | `true` when the pad is physically clicked (haptic click). |

Updated on every trackpad position change and on every click event.

---

### `last_event`

The most recently processed input event and what makima actually emitted.

| Field | Type | Meaning |
|---|---|---|
| `input` | `string` | Button that was pressed/released, e.g. `"BTN_SOUTH"` |
| `action` | `[string]` | Output keys that were emitted, e.g. `["KEY_ENTER"]` |
| `kind` | `string` | `"remap"` / `"command"` / `"passthrough"` |
| `value` | `number` | `1` = press, `0` = release |

`null` until the first button is pressed after makima starts.

---

## Frontend Logic

### Which bindings to display

```
if held_modifiers is non-empty and modifier_active is non-empty:
    display = modifier_active     ← only combos reachable from current modifier
else:
    display = bindings            ← all bindings
```

### Button highlighting

```
for each button in layout:
    if button in active_buttons:
        highlight(button, "held")
    elif last_event.input == button and last_event.value == 1:
        highlight(button, "just_pressed")   ← optional, fades out
    else:
        unhighlight(button)
```

### Modifier indicator

```
if held_modifiers contains "BTN_TL":
    show_modifier_indicator("L1")
```

### Paused state

```
if context.paused:
    show_overlay("preview mode — no output")
```

---

## Button Name Reference (Steam Deck)

| `bindings` key | Physical button |
|---|---|
| `BTN_SOUTH` | A |
| `BTN_EAST` | B |
| `BTN_NORTH` | X |
| `BTN_WEST` | Y |
| `BTN_TL` | L1 |
| `BTN_TR` | R1 |
| `BTN_TL2` | L2 (analog, treated as button) |
| `BTN_TR2` | R2 (analog, treated as button) |
| `BTN_THUMBL` | L3 (left stick click) |
| `BTN_THUMBR` | R3 (right stick click) |
| `BTN_SELECT` | Select / View |
| `BTN_START` | Start / Menu |
| `BTN_MODE` | Steam button |
| `BTN_GRIPL` | L5 (upper left back paddle) |
| `BTN_GRIPL2` | L4 (lower left back paddle) |
| `BTN_GRIPR` | R5 (upper right back paddle) |
| `BTN_GRIPR2` | R4 (lower right back paddle) |
| `BTN_DPAD_UP/DOWN/LEFT/RIGHT` | D-Pad |

---

## Update Frequency

- On every button press and release
- On modifier state change (held_modifiers changes)
- On config switch (active window changes)
- On pause/resume via IPC socket
- On every trackpad position update (when `LPAD`/`RPAD = "trackpad"`)

The file is **not** updated continuously — only on events. The frontend does not need to poll.

---

## IPC — Pause / Resume

To pause makima output (e.g. when HUD opens):

```bash
echo "pause" | socat - UNIX-CONNECT:/tmp/makima-control.sock
```

To resume:

```bash
echo "resume" | socat - UNIX-CONNECT:/tmp/makima-control.sock
```

The socket may not exist if makima is not running — handle gracefully (socat fails silently).
`context.paused` reflects the current state after each command.
