# Makima State — Frontend Integration Guide

## Overview

Makima writes `/tmp/makima-state.json` atomically after every relevant input event.
The file is updated via `rename()` so reads are always consistent — no partial writes.

Watch for changes using inotify on the **directory**, not the file itself (atomic rename
creates a new inode each time, so watching the file directly loses events):

```bash
inotifywait -m -e moved_to /tmp/ 2>/dev/null | grep --line-buffered "makima-state.json" | while read _; do
  python3 -c "
import json, datetime
d = json.load(open('/tmp/makima-state.json'))
t = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
lp = d['trackpads']['lpad']; rp = d['trackpads']['rpad']
ls = d['sticks']['lstick'];   rs = d['sticks']['rstick']
l2 = d['triggers']['l2'];     r2 = d['triggers']['r2']
print(f\"{t}  lpad({lp['x']:+.3f},{lp['y']:+.3f}{'T' if lp['touching'] else ' '}{'P' if lp['pressed'] else ' '})  rpad({rp['x']:+.3f},{rp['y']:+.3f}{'T' if rp['touching'] else ' '}{'P' if rp['pressed'] else ' '})  lstick({ls['x']:+.3f},{ls['y']:+.3f}{'*' if ls['active'] else ' '})  rstick({rs['x']:+.3f},{rs['y']:+.3f}{'*' if rs['active'] else ' '})  L2={l2['value']:.3f}{'P' if l2['pressed'] else ' '}  R2={r2['value']:.3f}{'P' if r2['pressed'] else ' '}\")
" 2>/dev/null
done
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
      "x": 0.170,
      "y": 0.039,
      "touching": true,
      "pressed": false
    },
    "rpad": {
      "mode": "trackpad",
      "x": 0.0,
      "y": 0.0,
      "touching": false,
      "pressed": false
    }
  },
  "sticks": {
    "lstick": {
      "mode": "disabled",
      "x": 0.023,
      "y": 0.006,
      "deadzone": 0.031,
      "active": false
    },
    "rstick": {
      "mode": "cursor",
      "x": -0.002,
      "y": 0.002,
      "deadzone": 0.092,
      "active": false
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
| `active_buttons` | `[string]` | All buttons currently physically held, including non-modifiers. **Use this to highlight buttons on the gamepad layout.** |

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

### `trackpads`

Always present. Both `lpad` and `rpad` are always included regardless of mode.

All position values are normalized to **−1.0 … +1.0**, rounded to 3 decimal places.

| Field | Type | Meaning |
|---|---|---|
| `mode` | `string` | `"trackpad"` or `"disabled"` — value of `LPAD`/`RPAD` config setting |
| `x` | `float` | Horizontal position −1.0…+1.0. `0.0` when not touching. |
| `y` | `float` | Vertical position −1.0…+1.0. `0.0` when not touching. Positive = up (hardware convention). |
| `touching` | `bool` | `true` when finger is on the pad. |
| `pressed` | `bool` | `true` when the pad is physically clicked. |

Updated on every trackpad position change and on every click event.

---

### `sticks`

Always present. Both `lstick` and `rstick` are always included regardless of mode.

All position values are normalized to **−1.0 … +1.0**, rounded to 3 decimal places.
The deadzone is expressed in the same normalized space — draw it directly as a circle radius.

| Field | Type | Meaning |
|---|---|---|
| `mode` | `string` | `"disabled"` / `"cursor"` / `"scroll"` / `"bind"` |
| `x` | `float` | Horizontal position −1.0…+1.0. |
| `y` | `float` | Vertical position −1.0…+1.0. |
| `deadzone` | `float` | Configured deadzone threshold in normalized space (0.0…1.0). Use as circle radius in the UI. |
| `active` | `bool` | `true` when either axis exceeds the deadzone. Ready-to-use — no threshold math needed. |

---

## Analog value notes

- All analog values (trackpads, sticks) use normalized floats, never raw hardware integers.
- Rounded to **3 decimal places** — values only change when the rounded result differs from the previous write. The frontend receives no sub-threshold noise.
- **Sticks**: `x`/`y` always reflect raw hardware position, regardless of `mode`. Even a `"disabled"` stick reports its physical position (useful for showing drift).
- **Trackpads**: `x`/`y` always reflect raw hardware position, regardless of `mode`. Position is reported even when mode is not `"trackpad"`.
- **Triggers (L2/R2)**: no analog axis on Steam Deck — use `active_buttons` for `BTN_TL2`/`BTN_TR2`.

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

### Stick visualization

```
// Draw deadzone circle with radius = stick.deadzone
// Place dot at (stick.x, stick.y)
// Tint ring or dot when stick.active == true
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

## Update Frequency

- On every button press and release
- On modifier state change (`held_modifiers` changes)
- On config switch (active window changes)
- On pause/resume via IPC socket
- On trackpad position change (when finger is on pad), rate-limited to ~60 Hz
- On trackpad touch/release (bypasses rate limit — always immediate)
- On trackpad click (press/release)
- On stick movement, rate-limited to ~60 Hz

**Analog writes are skipped entirely if no rounded value has changed** — the frontend will not receive spurious identical updates.

The file is **not** polled — only updated on events. Use inotify, not a timer.

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
| `BTN_TL2` | L2 (digital only — no analog axis on Steam Deck) |
| `BTN_TR2` | R2 (digital only — no analog axis on Steam Deck) |
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
