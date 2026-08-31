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
print(f\"{t}  lpad({lp['x']:+.3f},{lp['y']:+.3f}{'T' if lp['touching'] else ' '}{'P' if lp['pressed'] else ' '})  rpad({rp['x']:+.3f},{rp['y']:+.3f}{'T' if rp['touching'] else ' '}{'P' if rp['pressed'] else ' '})  lstick({ls['x']:+.3f},{ls['y']:+.3f}{'*' if ls['active'] else ' '})  rstick({rs['x']:+.3f},{rs['y']:+.3f}{'*' if rs['active'] else ' '}\")
" 2>/dev/null
done
```

---

## Full Schema

```json
{
  "lifecycle": "ready",
  "errors": {
    "base_config": "parse error in Steam Deck.toml line 12: unexpected token"
  },
  "configs": [
    { "name": "Steam Deck",                    "enabled": true,  "status": "ok",      "errors": [] },
    { "name": "Steam Deck::org.mozilla.firefox","enabled": true,  "status": "warning", "errors": [] },
    { "name": "Steam Deck::org.kde.konsole",   "enabled": false, "status": "ok",      "errors": [] }
  ],
  "context": {
    "active_app": "org.mozilla.firefox",
    "config_stack": ["Steam Deck", "org.mozilla.firefox"],
    "layout": 0,
    "paused": false,
    "gaming_mode": false,
    "held_modifiers": ["BTN_TL"],
    "active_buttons": ["BTN_TL", "BTN_SOUTH"],
    "active_outputs": [
      { "key": "KEY_LEFTCTRL", "silent": false }
    ],
    "available_modifiers": ["BTN_MODE"],
    "analog_state_export": false
  },
  "bindings": {
    "BTN_SOUTH": {
      "action": ["KEY_ENTER"],
      "kind": "remap",
      "label": null,
      "origin": "Steam Deck",
      "silent": false
    },
    "BTN_TL-BTN_GRIPR2": {
      "action": ["KEY_LEFTCTRL", "KEY_PAGEDOWN"],
      "kind": "remap",
      "label": "Next Tab",
      "origin": "Steam Deck",
      "silent": false
    },
    "BTN_THUMBL": {
      "action": ["deckery-hud-toggle"],
      "kind": "command",
      "label": "Toggle HUD",
      "origin": "Steam Deck",
      "no_pause": true
    }
  },
  "modifier_active": {
    "BTN_GRIPR2": {
      "action": ["KEY_LEFTCTRL", "KEY_PAGEDOWN"],
      "kind": "remap",
      "label": "Next Tab",
      "origin": "Steam Deck"
    }
  },
  "gaming_mode_trigger": {
    "key": "BTN_BASE",
    "label": "Toggle Gaming Mode"
  },
  "last_action": {
    "type": "keys",
    "value": ["KEY_ENTER"],
    "label": null,
    "ts": 1234567890.123
  },
  "trackpads": {
    "lpad": {
      "mode": "mt-trackpad",
      "x": 0.170,
      "y": 0.039,
      "touching": true,
      "pressed": false
    },
    "rpad": {
      "mode": "mt-trackpad",
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
  },
  "imu": {
    "x": 0.512,
    "y": 0.489
  }
}
```

---

## Fields

### `lifecycle`

String describing the current startup/reinitialisation phase of makima.

| Value | Meaning |
|---|---|
| `"ready"` | Normal operation — fully initialised and processing input |
| `"starting"` | First startup in progress — device grabs not yet complete |
| `"reinitialising"` | Reinitialising after a device reconnect or resume — temporarily amber in the tray |
| `""` | File absent or written by an older makima build that doesn't export this field |

The tray shows an amber icon whenever `lifecycle` is `"starting"` or `"reinitialising"`, even if all services report `active`.

---

### `errors`

Object mapping error slot names to human-readable error strings. Empty `{}` when there are no errors.

| Key | When present |
|---|---|
| `"base_config"` | The base config (`Steam Deck.toml`) failed to parse — all remapping is suspended |
| `"no_device"` | No compatible input device was found — makima is waiting for one to appear |

When any key is present the tray shows a red icon, regardless of service state.

---

### `configs`

Array of all config files known to makima, in the order they appear on disk. Updated whenever configs are loaded, reloaded, or their enabled state changes.

Each entry:

| Field | Type | Meaning |
|---|---|---|
| `name` | `string` | Config identifier — base configs use the device name (e.g. `"Steam Deck"`); app overrides use `"Device::app.class"` (e.g. `"Steam Deck::org.mozilla.firefox"`) |
| `enabled` | `bool` | Whether this config is active. Base configs (`"::"` absent) are always enabled and cannot be toggled by the user. |
| `status` | `string` | `"ok"`, `"warning"`, or `"error"` — `"error"` means the config could not be parsed and its slot in `errors` is populated |
| `errors` | `[{message}]` | Parse or load errors for this config; empty when `status != "error"` |

The tray's **Controller Bindings** submenu is driven directly from this array. Toggling a config via the tray sends a `config enable/disable <name>` IPC command, which updates `enabled` and rewrites this field.

---

### `context`

| Field | Type | Meaning |
|---|---|---|
| `active_app` | `string` | Active app class, e.g. `"org.mozilla.firefox"`. `"default"` when no app-specific config is loaded. |
| `config_stack` | `[string]` | Active config name(s). One entry = base config only; two entries = base + app override. |
| `layout` | `number` | Active layout index (0–3). For multi-layout configs. |
| `paused` | `bool` | Makima is paused — no output is emitted. Set when HUD opens. |
| `gaming_mode` | `bool` | Gaming Mode is active — all remaps suppressed, raw input passed through. |
| `held_modifiers` | `[string]` | Modifier buttons currently physically held (e.g. `["BTN_TL"]`). Empty when no modifier is held. **Use this to switch between normal and modifier view.** |
| `active_buttons` | `[string]` | All buttons currently physically held, including non-modifiers. **Use this to highlight buttons on the gamepad layout.** |
| `active_outputs` | `[{key, silent}]` | System-level output keys currently being held, resolved from `active_buttons` + current modifiers. Each entry: `{ "key": "KEY_LEFTCTRL", "silent": false }`. |
| `available_modifiers` | `[string]` | Modifier buttons that, if pressed next, would unlock additional combo bindings. Use to hint which modifiers are worth showing in the HUD. |
| `analog_state_export` | `bool` | Whether analog data (sticks, trackpads) is currently being written into this file. |

---

### `bindings`

Complete map of all configured button actions for the current config.

Key format:
- `"BTN_SOUTH"` — plain binding, no modifier
- `"BTN_TL-BTN_GRIPR2"` — combo: BTN_TL held, BTN_GRIPR2 pressed

Value fields:

| Field | Type | Meaning |
|---|---|---|
| `action` | `[string]` | Output keys (remap) or shell commands (command) |
| `kind` | `string` | `"remap"` / `"command"` / `"movement"` |
| `label` | `string\|null` | Human-readable binding name, or `null` if not configured |
| `origin` | `string` | Config file this binding comes from |
| `silent` | `bool` | If `true`, this binding is intentionally hidden from the HUD display |
| `no_pause` | `bool` | (command only) Fires even when makima is paused |

**This map is static while the config doesn't change.** Reload it when `context.config_stack` or `context.layout` changes.

---

### `modifier_active`

Subset of `bindings` — only the combos reachable with the currently held modifiers, keyed by trigger button name only (modifier prefix stripped).

Example: if `BTN_TL` is held, `modifier_active` contains all `BTN_TL-*` entries, keyed as `"BTN_GRIPR2"` etc.

Empty `{}` when no modifier is held.

**Use this to replace `bindings` in the display when `held_modifiers` is non-empty.**

---

### `gaming_mode_trigger`

The configured Gaming Mode toggle button. `null` if the trigger is disabled (`trigger = { key = "disabled" }` in config).

| Field | Type | Meaning |
|---|---|---|
| `key` | `string` | Button name, e.g. `"BTN_BASE"` |
| `label` | `string` | Always `"Gaming Mode"` |

Use this to label the QAM / three-dot button in the HUD without hardcoding the key name.

See [Gaming Mode](../projects/makima-deckery/gaming-mode.md) for the full Gaming Mode reference.

---

### `last_action`

The most recently processed discrete user action. `null` until the first action occurs.

| Field | Type | Meaning |
|---|---|---|
| `type` | `string` | `"keys"` / `"command"` / `"movement"` |
| `value` | any | Output keys array, command string array, or movement description |
| `label` | `string\|null` | Human-readable label. Set from binding `label =` config, or generated (e.g. `"Gaming Mode On"` / `"Gaming Mode Off"` for Gaming Mode changes). |
| `ts` | `float` | Unix timestamp (seconds since epoch, millisecond precision) |
| `silent` | `bool` | When `true`, the HUD suppresses the toast for this action. |

Gaming Mode changes (double-click trigger, IPC commands, Steam auto-detection) always set `last_action` with `type: "command"` — even in pause/preview mode, so the HUD can show the action in its preview toast without actually toggling the mode.

---

### `trackpads`

Always present. Both `lpad` and `rpad` are always included regardless of mode.

All position values are normalized to **−1.0 … +1.0**, rounded to 3 decimal places.

| Field | Type | Meaning |
|---|---|---|
| `mode` | `string` | `"mt-trackpad"`, `"disabled"` — value of `[trackpad.left/right] mode` |
| `x` | `float` | Horizontal position −1.0…+1.0. `0.0` when not touching. |
| `y` | `float` | Vertical position −1.0…+1.0. `0.0` when not touching. Positive = up. |
| `touching` | `bool` | `true` when finger is on the pad. |
| `pressed` | `bool` | `true` when the pad is physically clicked. |

---

### `sticks`

Always present. Both `lstick` and `rstick` are always included regardless of mode.

| Field | Type | Meaning |
|---|---|---|
| `mode` | `string` | `"disabled"` / `"cursor"` / `"scroll"` / `"bind"` |
| `x` | `float` | Horizontal position −1.0…+1.0. |
| `y` | `float` | Vertical position −1.0…+1.0. |
| `deadzone` | `float` | Configured deadzone in normalized space (0.0…1.0). Use as circle radius. |
| `active` | `bool` | `true` when either axis exceeds the deadzone. |

---

### `imu`

Gyroscope/accelerometer axes, normalized to 0.0…1.0.

| Field | Type | Meaning |
|---|---|---|
| `x` | `float` | ABS_HAT2X axis normalized |
| `y` | `float` | ABS_HAT2Y axis normalized |

Only populated when `analog_state_export` is active.

---

## Frontend Logic

### Which bindings to display

```
if held_modifiers is non-empty and modifier_active is non-empty:
    display = modifier_active     ← only combos reachable from current modifier
else:
    display = bindings            ← all bindings
```

### Gaming Mode state

```
if context.gaming_mode:
    show_badge("Gaming Mode")
    // bindings are suppressed — raw input goes to game
```

### QAM / trigger button label

```
if gaming_mode_trigger != null:
    label(gaming_mode_trigger.key, gaming_mode_trigger.label)
```

### Button highlighting

```
for each button in layout:
    if button in active_buttons:
        highlight(button, "held")
    elif last_action.value contains mapped_key(button) and recent:
        highlight(button, "just_pressed")
    else:
        unhighlight(button)
```

### Stick visualization

```
// Draw deadzone circle with radius = stick.deadzone
// Place dot at (stick.x, stick.y)
// Tint ring or dot when stick.active == true
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
- On pause/resume or Gaming Mode change via IPC socket
- On trackpad position change (when finger is on pad), rate-limited to ~60 Hz
- On trackpad touch/release — always immediate
- On trackpad click (press/release)
- On stick movement, rate-limited to ~60 Hz

**Analog writes are skipped entirely if no rounded value has changed.**

The file is **not** polled — only updated on events. Use inotify, not a timer.

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
| `BTN_TL2` | L2 (digital only) |
| `BTN_TR2` | R2 (digital only) |
| `BTN_THUMBL` | L3 (left stick click) |
| `BTN_THUMBR` | R3 (right stick click) |
| `BTN_SELECT` | Select / View |
| `BTN_START` | Start / Menu |
| `BTN_MODE` | Steam button |
| `BTN_BASE` | QAM / three-dot button |
| `BTN_GRIPL` | L5 (upper left back paddle) |
| `BTN_GRIPL2` | L4 (lower left back paddle) |
| `BTN_GRIPR` | R5 (upper right back paddle) |
| `BTN_GRIPR2` | R4 (lower right back paddle) |
| `BTN_DPAD_UP/DOWN/LEFT/RIGHT` | D-Pad |
